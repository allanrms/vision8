import traceback
from datetime import datetime
from typing import Tuple

from django.utils import timezone
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from agents.models import LLMProviderConfig
from agents.services import create_llm_service
from authentication.models import User
from utils.ai_assistants import IntentRouterAssistant
from whatsapp_connector.models import MessageHistory, EvolutionInstance
from whatsapp_connector.services import ImageProcessingService, EvolutionAPIService
from whatsapp_connector.utils import transcribe_audio_from_bytes, clean_number_whatsapp

# from django_ai_assistant.models import Thread  # Não usar - desabilitado


# @method_decorator(csrf_exempt, name='dispatch')
class EvolutionWebhookView(APIView):
    permission_classes = (AllowAny,)
    
    def post(self, request, *args, **kwargs):
        """
        Handle incoming webhooks from Evolution API
        """
        try:
            data = request.data
            response_msg = None

            # Validate webhook data
            if not self._validate_webhook_data(data):
                return Response(
                    {'error': 'Invalid webhook data'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Extract message data
            message_data = self._extract_message_data(data)
            
            if not message_data:
                return Response(
                    {'status': 'ignored', 'reason': 'Not a valid message'}, 
                    status=status.HTTP_200_OK
                )

            # Get Evolution instance
            evolution_instance = self._get_evolution_instance(message_data)

            # Save message to database and get WhatsApp contact user
            message_history, whatsapp_user = self._save_message(message_data, evolution_instance)

            # Check and process admin commands (activate/deactivate instance)
            admin_response = self._process_admin_commands(message_history, evolution_instance)
            if admin_response:
                return admin_response

            # Check and process calendar commands
            # calendar_response = self._process_calendar_commands(message_history, evolution_instance)
            # if calendar_response:
            #     return calendar_response

            # Verifique se a instância está ativa - caso contrário, ignore a mensagem
            if evolution_instance and not evolution_instance.is_active:
                print(f"🔴 Instância inativa, ignorando mensagem: {evolution_instance.name}")
                return Response({
                    'status': 'ignored',
                    'reason': 'Instância está inativa',
                    'message_id': message_history.message_id
                }, status=status.HTTP_200_OK)

            # Verifique se deve ignorar as próprias mensagens (somente se não for um comando de administrador)
            ignore_response = self._should_ignore_own_message(message_history, evolution_instance)
            if ignore_response:
                return ignore_response

            # Verifique se o remetente tem permissão para usar o serviço usando a configuração da instância
            auth_response = self._validate_authorized_number(message_history, evolution_instance)
            if auth_response:
                return auth_response

            # Inicializar serviços
            evolution_api = EvolutionAPIService(evolution_instance)
            # n8n_service = N8NService()  # Comentado - usando OpenAI via agents

            print(f"Processando mensagem: {message_history.message_type} de {message_history.sender_name}")
            print(f"Has image: {message_data.get('has_image')}, Has audio: {message_data.get('has_audio')}")
            print(f"Media URL: {message_history.media_url}")

            # Processar diferentes tipos de mensagens como o aplicativo Orbi
            if message_data.get('has_audio') or message_history.message_type == 'audio':
                message_history = self._process_audio_message(message_history, evolution_api, data)

            elif message_data.get('has_image') or message_history.message_type == 'image':
                message_history = self._process_image_message(message_history, data, evolution_instance)

            if message_history.content:
            # elif message_history.content or message_history.message_type == 'text':  # Text message
                # Marcar como processando
                message_history.processing_status = 'processing'
                message_history.save()

                # intent_router_assistant = IntentRouterAssistant()
                #
                # # Não usar Thread do django-ai-assistant (desabilitado)
                # config_type = intent_router_assistant.run(
                #     message=message_history.content,
                #     thread_id=None  # Sem thread persistente
                # )

                llm_config = LLMProviderConfig.objects.filter(config_type='finance').first()

                if llm_config:
                    ai = create_llm_service(llm_config, user=whatsapp_user)
                    response_msg = ai.send_text_message(message_history.content, message_history.chat_session)
                else:
                    # Fallback: usar configuração padrão ou mostrar erro
                    response_msg = "⚠️ Nenhuma configuração de IA foi encontrada para esta instância. Configure um LLM Provider no painel administrativo."

            # Processar resposta estruturada ou simples - só se houver resposta
            result = False
            if response_msg:

                result = self._send_response_to_whatsapp(evolution_api, message_history.chat_session.from_number, response_msg)

                # Atualizar o MessageHistory com a resposta
                if result and not isinstance(result, dict):
                    # Resposta enviada com sucesso
                    message_history.response = response_msg
                    message_history.processing_status = 'completed'
                    message_history.save()
                    print(f"✅ Resposta enviada e salva para mensagem {message_history.message_id}")
                elif isinstance(result, dict) and result.get('error') == 'number_not_exists':
                    # Número não tem WhatsApp
                    message_history.processing_status = 'failed'
                    message_history.response = f"❌ Número {result.get('number')} não tem WhatsApp"
                    message_history.save()
                    print(f"⚠️ Número {result.get('number')} não tem WhatsApp - mensagem não enviada")
                    result = True  # Considerar como sucesso pois foi processado corretamente
                else:
                    message_history.processing_status = 'failed'
                    message_history.save()
                    print(f"❌ Erro ao enviar resposta para {message_history.chat_session.from_number}")
            else:
                # Sem resposta - marcar como processado mas sem resposta (sessão humana/encerrada)
                message_history.processing_status = 'completed'
                message_history.save()
                print(f"ℹ️ Mensagem processada sem resposta para {message_history.chat_session.from_number} (sessão em atendimento humano ou encerrada)")
                result = True  # Considerar como sucesso pois foi processado corretamente

            if result:
                return Response({
                    'status': 'success',
                    'message': 'Message sent successfully',
                    'result': result
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'error',
                    'message': 'Failed to send message'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


        except Exception as e:
            print(f"Error processing webhook: {e}")
            traceback.print_exc()
            return Response(
                {'error': 'Internal server error'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _validate_webhook_data(self, data):
        """Validate that webhook data has required fields"""
        return isinstance(data, dict) and 'data' in data
    
    def _extract_message_data(self, webhook_data):
        """Extract message data from webhook payload - integrated with orbi logic"""
        try:
            data = webhook_data.get('data', {})

            print(data)
            
            if not data:
                return None
                
            # Extract basic info like orbi app
            sender_jid = data.get('key', {}).get('remoteJid', '')
            sender_name = data.get('pushName', '')
            source = data.get('source', '')
            message_timestamp = data.get('messageTimestamp', 0)
            
            # Apply same filtering logic as orbi (customize as needed)
            # if sender_name != "Allan Ramos" and sender_jid != "558399330465@s.whatsapp.net":
            #     return None
            
            # Handle different webhook event types
            if 'message' in data:
                message_data = data['message']
                
                # Extract content based on message type like orbi
                text_message = None
                audio_message = None
                image_message = None
                
                # Detectar tipo de mensagem baseado na estrutura real
                if 'conversation' in message_data:
                    text_message = message_data['conversation']
                elif 'extendedTextMessage' in message_data:
                    text_message = message_data['extendedTextMessage'].get('text')
                elif 'imageMessage' in message_data:
                    image_message = message_data['imageMessage']
                    # Para imagens, o caption é o texto da mensagem
                    text_message = message_data['imageMessage'].get('caption', '')
                elif 'audioMessage' in message_data:
                    audio_message = message_data['audioMessage'].get('url')
                elif 'videoMessage' in message_data:
                    image_message = message_data['videoMessage']  # Tratar vídeo similar a imagem para processamento
                elif 'documentMessage' in message_data:
                    image_message = message_data['documentMessage']
                
                # Buscar to_number a partir do owner da instância
                to_number = data.get('instance', '')
                owner = data.get('owner')
                if not to_number and owner:
                    # Tentar buscar o phone_number da instância Evolution pelo owner
                    try:
                        from whatsapp_connector.models import EvolutionInstance
                        evolution_instance = EvolutionInstance.objects.get(instance_name=owner)
                        to_number = evolution_instance.phone_number or owner
                    except EvolutionInstance.DoesNotExist:
                        to_number = owner
                
                return {
                    'message_id': data.get('key', {}).get('id'),
                    'from_number': sender_jid,
                    'to_number': to_number,
                    'message_type': self._get_message_type(message_data),
                    'content': text_message or self._get_message_content(message_data),
                    'media_url': self._get_media_url(message_data),
                    'timestamp': timezone.make_aware(datetime.fromtimestamp(message_timestamp)) if message_timestamp else timezone.now(),
                    'sender_name': sender_name,
                    'source': source,
                    'raw_data': data,
                    'has_audio': bool(audio_message),
                    'has_image': bool(image_message)
                }
            
            return None
            
        except Exception as e:
            print(f"Error extracting message data: {e}")
            return None
    
    def _get_message_type(self, message):
        """Determine message type from message object"""
        # Primeiro verifica se é um objeto message direto
        if 'imageMessage' in message:
            return 'image'
        elif 'audioMessage' in message:
            return 'audio'
        elif 'videoMessage' in message:
            return 'video'
        elif 'documentMessage' in message:
            return 'document'
        # Senão verifica dentro de message.message (estrutura aninhada)
        elif 'imageMessage' in message.get('message', {}):
            return 'image'
        elif 'audioMessage' in message.get('message', {}):
            return 'audio'
        elif 'videoMessage' in message.get('message', {}):
            return 'video'
        elif 'documentMessage' in message.get('message', {}):
            return 'document'
        else:
            return 'text'
    
    def _get_message_content(self, message):
        """Extract text content from message"""
        # Primeiro verifica se é um objeto message direto
        if 'conversation' in message:
            return message['conversation']
        elif 'extendedTextMessage' in message:
            return message['extendedTextMessage'].get('text', '')
        elif 'imageMessage' in message:
            return message['imageMessage'].get('caption', '')
        
        # Senão verifica dentro de message.message (estrutura aninhada)
        msg_content = message.get('message', {})
        if 'conversation' in msg_content:
            return msg_content['conversation']
        elif 'extendedTextMessage' in msg_content:
            return msg_content['extendedTextMessage'].get('text', '')
        elif 'imageMessage' in msg_content:
            return msg_content['imageMessage'].get('caption', '')
        
        return ''
    
    def _get_media_url(self, message):
        """Extract media URL from message"""
        # Primeiro verifica se é um objeto message direto
        if 'imageMessage' in message:
            return message['imageMessage'].get('url', '')
        elif 'audioMessage' in message:
            return message['audioMessage'].get('url', '')
        elif 'videoMessage' in message:
            return message['videoMessage'].get('url', '')
        elif 'documentMessage' in message:
            return message['documentMessage'].get('url', '')
        
        # Senão verifica dentro de message.message (estrutura aninhada)
        msg_content = message.get('message', {})
        if 'imageMessage' in msg_content:
            return msg_content['imageMessage'].get('url', '')
        elif 'audioMessage' in msg_content:
            return msg_content['audioMessage'].get('url', '')
        elif 'videoMessage' in msg_content:
            return msg_content['videoMessage'].get('url', '')
        elif 'documentMessage' in msg_content:
            return msg_content['documentMessage'].get('url', '')
        
        return None
    
    def _save_message(self, message_data, evolution_instance=None) -> tuple[MessageHistory, User]:
        """Save message to database"""
        from whatsapp_connector.models import ChatSession
        from django.conf import settings

        # Get or create chat session first
        from_number = clean_number_whatsapp(message_data['from_number'])
        to_number = clean_number_whatsapp(message_data.get('to_number', ''))

        print(f'from_number {from_number} to_number {to_number}')

        user_whatsapp_contact, user_created, password = self._get_or_create_user(from_number, message_data.get('sender_name', ''))

        # Buscar sessão ativa (ai ou human) ou criar nova com status 'ai'
        chat_session, session_created = ChatSession.get_or_create_active_session(
            from_number=from_number,
            to_number=to_number,
            evolution_instance=evolution_instance,
            owner=user_whatsapp_contact
        )


        if session_created:
            print(f"✅ Nova sessão criada para {from_number} com status 'ai'")

            # Se o usuário foi criado agora, enviar mensagem de boas-vindas
            if user_created and password and evolution_instance:
                evolution_api = EvolutionAPIService(evolution_instance)
                dashboard_url = getattr(settings, 'DASHBOARD_URL', 'https://seu-dashboard.com')

                welcome_msg = f"""🎉 *Bem-vindo ao nosso sistema de gestão financeira!*

Sua conta foi criada com sucesso! 

📊 Seu perfil já está configurado com mais de 60 categorias financeiras prontas para uso!

💬 *Como usar:*
• Envie suas despesas ou receitas diretamente por mensagem ou áudio.
• Exemplo: "Gastei R$ 50 no supermercado"
• Exemplo: "Recebi R$ 1.200 de salário"
• "Mostrar meus gastos do mês"
• "Qual meu saldo por categoria?"
• Solicite análises personalizadas dos seus gastos e receitas.
• Você também pode enviar áudios, e eu registro tudo para você.


Aqui estão suas credenciais de acesso, caso queira acompanhar tudo em um dashboard:

👤 *Login:* {user_whatsapp_contact.username}
🔐 *Senha:* {password}
🌐 *Acesse:* {dashboard_url}

💡 *Dica:* Guarde suas credenciais em um local seguro. Você pode usar o sistema via WhatsApp ou acessar o dashboard pelo link acima."""

                evolution_api.send_text_message(from_number, welcome_msg)
                print(f"📨 Mensagem de boas-vindas enviada para {from_number}")
        else:
            print(f"ℹ️ Usando sessão existente para {from_number} (status: {chat_session.get_status_display()})")

        # Extract data for database saving (remove helper fields)
        save_data = message_data.copy()
        save_data.pop('has_audio', None)
        save_data.pop('has_image', None)
        save_data.pop('from_number', None)  # Remove since it's in chat_session
        save_data.pop('to_number', None)    # Remove since it's in chat_session
        
        # Check if instance is inactive and mark the message
        if evolution_instance and not evolution_instance.is_active:
            save_data['received_while_inactive'] = True
            print(f"🔴 Marcando mensagem como recebida com instância inativa: {evolution_instance.name}")
        else:
            save_data['received_while_inactive'] = False
        
        # Add chat_session
        save_data['chat_session'] = chat_session
        save_data['owner'] = user_whatsapp_contact

        # Set created_at from timestamp if available
        if 'timestamp' in save_data:
            save_data['created_at'] = save_data.pop('timestamp')
        
        message_history, created = MessageHistory.objects.get_or_create(
            message_id=message_data['message_id'],
            defaults=save_data
        )
        return message_history, user_whatsapp_contact
    
    def _process_audio_message(self, message, evolution_api, raw_data) -> str:
        """Process audio message like orbi app"""
        try:
            print("Mensagem de áudio detectada")
            message.processing_status = 'processing'
            message.save()
            
            # Decrypt audio using the same logic as orbi
            audio_bytes = evolution_api.decrypt_whatsapp_audio(raw_data)
            
            if audio_bytes:
                # Transcribe audio
                transcription = transcribe_audio_from_bytes(audio_bytes.read())
                print(f"Texto transcrito: {transcription}")
                
                message.audio_transcription = transcription
                message.content = transcription  # Use transcription as message content
                message.save()
            else:
                print("❌ Falha ao descriptografar áudio")
                message.processing_status = 'failed'
                message.save()

        except Exception as e:
            print(f"Error processing audio message: {e}")
            message.processing_status = 'failed'
            message.save()

        finally:
            return message
    
    def _process_text_message(self, message, n8n_service):
        """Process text message like orbi app"""
        try:
            print(f"Mensagem de texto detectada {message}")
            message.processing_status = 'processing'
            message.save()
            
            # Send to n8n
            n8n_result = n8n_service.send_message_to_n8n(
                message.from_number, 
                message.sender_name, 
                message.content
            )
            
            if n8n_result:
                message.n8n_response = n8n_result
                message.processing_status = 'completed'
            else:
                message.processing_status = 'failed'
                
            message.save()
            
        except Exception as e:
            print(f"Error processing text message: {e}")
            message.processing_status = 'failed'
            message.save()
    
    def _process_image_message(self, message, raw_data=None, evolution_instance=None):
        """Process image message with decryption support"""
        try:
            print("Mensagem de imagem detectada")
            message.processing_status = 'processing'
            message.save()
            
            processing_service = ImageProcessingService(evolution_instance)
            evolution_api = EvolutionAPIService(evolution_instance) if evolution_instance else None
            
            # Try to decrypt the image first if we have raw_data
            if raw_data:
                print("Tentando descriptografar imagem...")
                print(f"Raw data structure keys: {list(raw_data.keys())}")
                if 'data' in raw_data:
                    print(f"Data structure keys: {list(raw_data['data'].keys())}")
                    if 'message' in raw_data['data']:
                        print(f"Message structure keys: {list(raw_data['data']['message'].keys())}")
                
                decrypted_image = evolution_api.decrypt_whatsapp_image(raw_data)
                
                if decrypted_image:
                    print("✓ Descriptografia bem-sucedida")
                    # Save decrypted image directly
                    if processing_service.save_decrypted_image(decrypted_image, message):
                        # Process the decrypted image
                        processing_service.process_image_message(message)
                    else:
                        print("✗ Falha ao salvar imagem descriptografada")
                        message.processing_status = 'failed'
                        message.save()
                else:
                    print("Falha na descriptografia, tentando download direto...")
                    # Fallback to direct download
                    if message.media_url and processing_service.download_and_save_image(message.media_url, message):
                        processing_service.process_image_message(message)
                    else:
                        print("✗ Download direto também falhou")
                        message.processing_status = 'failed'
                        message.save()
            else:
                # No raw data, try direct download
                if message.media_url and processing_service.download_and_save_image(message.media_url, message):
                    processing_service.process_image_message(message)
                else:
                    message.processing_status = 'failed'
                    message.save()
                    
        except Exception as e:
            print(f"Error processing image message: {e}")
            message.processing_status = 'failed'
            message.save()

        finally:
            return message
    
    def _get_or_create_user(self, phone_number, sender_name=''):
        """
        Busca ou cria um usuário baseado no número de telefone
        Retorna tupla: (usuário, foi_criado, senha_ou_none)
        """
        from django.contrib.auth import get_user_model
        from finance.utils import create_default_categories
        import secrets
        import string

        User = get_user_model()

        username = phone_number
        email = f"{phone_number}@gmail.com"

        user, user_created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': sender_name,
            }
        )

        password = None

        if user_created:
            # Gerar senha aleatória única (12 caracteres)
            alphabet = string.ascii_letters + string.digits + string.punctuation
            password = ''.join(secrets.choice(alphabet) for _ in range(12))
            user.set_password(password)
            user.save()

            # Criar categorias padrão para o novo usuário
            categories_count = create_default_categories(user)

            print(f"✅ Usuário criado automaticamente: {username} ({email})")
            print(f"🔐 Senha gerada: {password}")
            print(f"📂 {categories_count} categorias padrão criadas")
        else:
            print(f"ℹ️ Usuário já existe: {username}")

        return user, user_created, password

    def _get_evolution_instance(self, message_data):
        """
        Busca a instância Evolution baseada no instanceId da mensagem
        """
        raw_data = message_data.get('raw_data', {})
        instance_id = raw_data.get('instanceId')
        owner = raw_data.get('owner')

        evolution_instance = None

        # Primeiro tentar por instanceId
        if instance_id:
            try:
                # Buscar por algum campo que corresponda ao instanceId
                # Como não temos um campo instanceId no modelo, vamos usar uma abordagem diferente
                print(f"🔍 Buscando instância por instanceId: {instance_id}")

                # Buscar todas as instâncias e verificar via API qual corresponde ao instanceId
                evolution_instance = EvolutionInstance.objects.get(instance_evolution_id=instance_id)

            except Exception as e:
                print(f"❌ Erro ao buscar instância por instanceId: {e}")


        return evolution_instance
    
    def _process_admin_commands(self, message_history, evolution_instance):
        """
        Processa comandos administrativos enviados pelo próprio número da instância
        Retorna Response se comando foi processado, None caso contrário
        """
        sender_number = message_history.chat_session.from_number

        # Processar comandos administrativos
        message_content = message_history.content.strip().lower() if message_history.content else ""
        evolution_api = EvolutionAPIService(evolution_instance)

        print(f'sender_number {sender_number} evolution_instance.phone_number {evolution_instance.phone_number}')

        # sender_number 558396194249 558399330465
        # sender_number 558396194249 558399330465

        if (evolution_instance and evolution_instance.phone_number) and message_history.sender_name == evolution_instance.profile_name:

            if message_content in ['<<<']:
                return self._handle_transfer_to_human_command(evolution_instance, evolution_api, sender_number,
                                                              message_history)

            elif message_content in ['>>>']:
                return self._handle_transfer_to_ai_command(evolution_instance, evolution_api, sender_number,
                                                           message_history)

            elif message_content in ['[]']:
                return self._handle_close_session_command(evolution_instance, evolution_api, sender_number, message_history)

        # Verificar se a mensagem é do próprio número da instância
        if not (evolution_instance and 
                evolution_instance.phone_number and 
                sender_number == evolution_instance.phone_number):
            return None

        if message_content in ['ativar', 'ativar instancia', 'ligar', 'on']:
            return self._handle_activate_command(evolution_instance, evolution_api, sender_number, message_history)
            
        elif message_content in ['desativar', 'desativar instancia', 'desligar', 'off']:
            return self._handle_deactivate_command(evolution_instance, evolution_api, sender_number, message_history)
            
        elif message_content in ['status', 'estado', 'info']:
            return self._handle_status_command(evolution_instance, evolution_api, sender_number, message_history)

        return None

    def _handle_activate_command(self, evolution_instance, evolution_api, sender_number, message_history):
        """Handle activate instance command"""
        if not evolution_instance.is_active:
            evolution_instance.is_active = True
            evolution_instance.save(update_fields=['is_active'])
            print(f"✅ Instância ativada via comando: {evolution_instance.name}")
            
            confirmation_msg = f"✅ Instância '{evolution_instance.name}' foi ativada com sucesso!"
            evolution_api.send_text_message(sender_number, confirmation_msg)
            
            return Response({
                'status': 'success',
                'reason': 'Instância ativada via comando',
                'message_id': message_history.message_id
            }, status=status.HTTP_200_OK)
        else:
            info_msg = f"ℹ️ A instância '{evolution_instance.name}' já está ativa."
            evolution_api.send_text_message(sender_number, info_msg)
            
            return Response({
                'status': 'ignored',
                'reason': 'Instância já estava ativa',
                'message_id': message_history.message_id
            }, status=status.HTTP_200_OK)
    
    def _handle_deactivate_command(self, evolution_instance, evolution_api, sender_number, message_history):
        """Handle deactivate instance command"""
        if evolution_instance.is_active:
            evolution_instance.is_active = False
            evolution_instance.save(update_fields=['is_active'])
            print(f"🔴 Instância desativada via comando: {evolution_instance.name}")
            
            confirmation_msg = f"🔴 Instância '{evolution_instance.name}' foi desativada com sucesso!"
            evolution_api.send_text_message(sender_number, confirmation_msg)
            
            return Response({
                'status': 'success',
                'reason': 'Instância desativada via comando',
                'message_id': message_history.message_id
            }, status=status.HTTP_200_OK)
        else:
            info_msg = f"ℹ️ A instância '{evolution_instance.name}' já está desativada."
            evolution_api.send_text_message(sender_number, info_msg)
            
            return Response({
                'status': 'ignored',
                'reason': 'Instância já estava desativada',
                'message_id': message_history.message_id
            }, status=status.HTTP_200_OK)
    
    def _handle_status_command(self, evolution_instance, evolution_api, sender_number, message_history):
        """Handle status info command"""
        status_icon = "✅" if evolution_instance.is_active else "🔴"
        status_text = "ativa" if evolution_instance.is_active else "desativada"
        
        status_msg = f"{status_icon} Instância '{evolution_instance.name}' está {status_text}.\n\n"
        status_msg += f"📱 Número: {evolution_instance.phone_number}\n"
        status_msg += f"🔗 Status de conexão: {evolution_instance.get_status_display()}\n"
        
        if evolution_instance.ignore_own_messages:
            status_msg += "🛡️ Filtro de mensagens próprias: Ativo\n"
        else:
            status_msg += "⚠️ Filtro de mensagens próprias: Inativo\n"
            
        status_msg += "\n💬 Comandos disponíveis:\n• 'ativar' - Ativa a instância\n• 'desativar' - Desativa a instância\n• 'status' - Mostra este status\n• '<<< +5511999999999' - Transfere sessão para humano\n• '>>> +5511999999999' - Retorna sessão para IA\n• '[ +5511999999999' - Encerra sessão"
        
        evolution_api.send_text_message(sender_number, status_msg)
        
        return Response({
            'status': 'success',
            'reason': 'Status da instância enviado',
            'message_id': message_history.message_id
        }, status=status.HTTP_200_OK)

    def _handle_transfer_to_human_command(self, evolution_instance, evolution_api, sender_number, message_history):
        """Handle transfer session to human command (<<<)"""
        try:
            # Buscar sessão
            from whatsapp_connector.models import ChatSession
            try:
                session = ChatSession.objects.filter(
                    from_number=message_history.chat_session.from_number,
                    evolution_instance=evolution_instance,
                    status='ai'
                ).update(status='human')

                success_msg = f"Sessão  transferida para atendimento humano"
                # evolution_api.send_text_message(sender_number, success_msg)

                return Response({
                    'status': 'success',
                    'reason': f'Sessão  transferida para humano',
                    'message_id': message_history.message_id
                }, status=status.HTTP_200_OK)

            except ChatSession.DoesNotExist:
                error_msg = f"❌ Sessão não encontrada para {message_history} \n\n"
                error_msg += "💡 Certifique-se de que o número está correto e já enviou mensagens"
                evolution_api.send_text_message(sender_number, error_msg)

                return Response({
                    'status': 'error',
                    'reason': f'Sessão não encontrada para',
                    'message_id': message_history.message_id
                }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            error_msg = f"❌ Erro ao transferir sessão: {str(e)}"
            evolution_api.send_text_message(sender_number, error_msg)

            return Response({
                'status': 'error',
                'reason': f'Erro interno: {str(e)}',
                'message_id': message_history.message_id
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _handle_transfer_to_ai_command(self, evolution_instance, evolution_api, sender_number, message_history):
        """Handle transfer session to AI command (>>>)"""
        try:
            from whatsapp_connector.models import ChatSession
            try:
                session = ChatSession.objects.filter(
                    from_number=message_history.chat_session.from_number,
                    evolution_instance=evolution_instance,
                    status='human'
                ).update(status='ai')

                success_msg = f"Sessão retornada para atendimento por IA"
                # evolution_api.send_text_message(sender_number, success_msg)

                return Response({
                    'status': 'success',
                    'reason': f'Sessão {message_history.chat_session} retornada para AI',
                    'message_id': message_history.message_id
                }, status=status.HTTP_200_OK)

            except ChatSession.DoesNotExist:
                error_msg = f"❌ Sessão não encontrada para {message_history.chat_session}\n\n"
                error_msg += "💡 Certifique-se de que o número está correto e já enviou mensagens"
                evolution_api.send_text_message(sender_number, error_msg)

                return Response({
                    'status': 'error',
                    'reason': f'Sessão não encontrada para {message_history.chat_session}',
                    'message_id': message_history.message_id
                }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            error_msg = f"❌ Erro ao retornar sessão para AI: {str(e)}"
            evolution_api.send_text_message(sender_number, error_msg)

            return Response({
                'status': 'error',
                'reason': f'Erro interno: {str(e)}',
                'message_id': message_history.message_id
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _handle_close_session_command(self, evolution_instance, evolution_api, sender_number, message_history):
        """Handle close session command ([)"""
        try:
            from whatsapp_connector.models import ChatSession
            try:
                session = ChatSession.objects.filter(
                    from_number=message_history.chat_session.from_number,
                    evolution_instance=evolution_instance
                ).update(status='closed')

                success_msg = f"Sua sessão foi encerrada."
                evolution_api.send_text_message(sender_number, success_msg)

                return Response({
                    'status': 'success',
                    'reason': f'Sessão {message_history.chat_session} encerrada',
                    'message_id': message_history.message_id
                }, status=status.HTTP_200_OK)

            except ChatSession.DoesNotExist:
                error_msg = f"❌ Sessão não encontrada para {message_history.chat_session}\n\n"
                error_msg += "💡 Certifique-se de que o número está correto e já enviou mensagens"
                evolution_api.send_text_message(sender_number, error_msg)

                return Response({
                    'status': 'error',
                    'reason': f'Sessão não encontrada para {message_history.chat_session}',
                    'message_id': message_history.message_id
                }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            error_msg = f"❌ Erro ao encerrar sessão: {str(e)}"
            evolution_api.send_text_message(sender_number, error_msg)

            return Response({
                'status': 'error',
                'reason': f'Erro interno: {str(e)}',
                'message_id': message_history.message_id
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _should_ignore_own_message(self, message_history, evolution_instance):
        """
        Verifica se deve ignorar mensagem enviada pelo próprio número da instância
        Retorna Response se deve ignorar, None caso contrário
        """
        sender_name = message_history.sender_name

        if (evolution_instance and 
            evolution_instance.ignore_own_messages and 
            evolution_instance.profile_name and
            sender_name == evolution_instance.profile_name):
            
            print(f"🚫 Ignorando mensagem da própria instância: {sender_name}")
            return Response({
                'status': 'ignored',
                'reason': 'Mensagem enviada pela própria instância',
                'message_id': message_history.message_id
            }, status=status.HTTP_200_OK)
            
        return None
    
    def _validate_authorized_number(self, message_history, evolution_instance):
        """
        Valida se o número remetente está autorizado a usar a instância
        Retorna Response se não autorizado, None se autorizado
        """
        sender_number = message_history.chat_session.from_number
        
        if not evolution_instance.is_number_authorized(sender_number):
            authorized_numbers = evolution_instance.get_authorized_numbers_list()
            print(f"❌ Número não autorizado: {sender_number}")
            if authorized_numbers:
                print(f"📱 Números permitidos: {authorized_numbers}")
            
            return Response({
                'status': 'ignored',
                'reason': f'Número {sender_number} não está autorizado para esta instância',
                'message_id': message_history.message_id
            }, status=status.HTTP_200_OK)
        
        print(f"✅ Número autorizado: {sender_number}")
        return None
    
    def _send_response_to_whatsapp(self, evolution_api, to_number, response_msg):
        """
        Envia resposta para WhatsApp, detectando se é estruturada ou simples
        """
        # if isinstance(response_msg, dict) and response_msg.get("type") == "structured":
        #     # Resposta estruturada - enviar texto e arquivo separadamente
        #     return self._send_structured_response(evolution_api, to_number, response_msg)
        # else:
        #     # Resposta simples - enviar apenas texto
        return evolution_api.send_text_message(to_number, str(response_msg))
    
    def _send_structured_response(self, evolution_api, to_number, structured_response):
        """
        Envia resposta estruturada (texto + arquivo) separadamente
        """
        text = structured_response.get("text", "").strip()
        file_url = structured_response.get("file", "").strip()
        
        print(f"📤 Enviando resposta estruturada:")
        print(f"   Texto: {text[:100]}..." if len(text) > 100 else f"   Texto: {text}")
        print(f"   Arquivo: {file_url}")
        
        results = []
        
        # Enviar texto primeiro se não estiver vazio
        if text:
            text_result = evolution_api.send_text_message(to_number, text)
            results.append(text_result)
            print(f"✅ Texto enviado: {text_result}")
        
        # Enviar arquivo depois se não estiver vazio
        if file_url:
            # Verificar se é URL válida
            if file_url.startswith(('http://', 'https://')):
                file_result = evolution_api.send_file_message(to_number, file_url)
                results.append(file_result) 
                print(f"📎 Arquivo enviado: {file_result}")
            else:
                print(f"⚠️ URL de arquivo inválida: '{file_url}' - deve começar com http:// ou https://")
                # Enviar mensagem explicativa para o usuário
                error_message = f"❌ Não foi possível enviar o arquivo '{file_url}'. O sistema precisa de uma URL completa (ex: https://exemplo.com/arquivo.pdf)."
                error_result = evolution_api.send_text_message(to_number, error_message)
                results.append(error_result)
        
        # Retornar True se ao menos um envio foi bem sucedido
        return any(results)

class MessageListView(APIView):
    permission_classes = (AllowAny,)
    
    def get(self, request):
        """List all WhatsApp messages"""
        messages = MessageHistory.objects.all()[:50]  # Last 50 messages
        
        data = []
        for message in messages:
            data.append({
                'message_id': message.message_id,
                'from_number': message.chat_session.from_number if message.chat_session else None,
                'to_number': message.chat_session.to_number if message.chat_session else None,
                'message_type': message.message_type,
                'content': message.content,
                'timestamp': message.created_at,
                'received_at': message.received_at,
                'processing_status': message.processing_status,
                'has_response': bool(message.response),
                'received_while_inactive': message.received_while_inactive,
            })
        
        return Response(data, status=status.HTTP_200_OK)

class MessageDetailView(APIView):
    permission_classes = (AllowAny,)
    
    def get(self, request, message_id):
        """Get detailed information about a specific message"""
        try:
            message = MessageHistory.objects.get(message_id=message_id)
            
            data = {
                'message_id': message.message_id,
                'from_number': message.chat_session.from_number if message.chat_session else None,
                'to_number': message.chat_session.to_number if message.chat_session else None,
                'message_type': message.message_type,
                'content': message.content,
                'media_url': message.media_url,
                'timestamp': message.created_at,
                'received_at': message.received_at,
                'processing_status': message.processing_status,
                'response': message.response,
                'received_while_inactive': message.received_while_inactive,
            }
            
            return Response(data, status=status.HTTP_200_OK)
            
        except MessageHistory.DoesNotExist:
            return Response(
                {'error': 'Message not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )



