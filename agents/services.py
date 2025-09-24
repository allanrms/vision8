from datetime import datetime
from django.conf import settings
from django_ai_assistant import AIAssistant
from django_ai_assistant.langchain.tools import method_tool
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage

from agents.models import LLMProviderConfig, ChatHistory, AssistantContextFile


def create_dynamic_assistant_class(llm_config: LLMProviderConfig, assistant_id: str = None):
    """
    Cria uma classe AIAssistant dinâmica baseada no LLMProviderConfig
    """

    class DynamicAIAssistant(AIAssistant):
        id = assistant_id or f"assistant_{llm_config.id}"
        name = llm_config.display_name or f"{llm_config.get_name_display()} - {llm_config.model}"
        instructions = llm_config.instructions or "Você é um assistente inteligente."
        model = llm_config.model

        def __init__(self):
            self.llm_config = llm_config
            super().__init__()

        def get_llm(self):
            """Retorna o modelo LLM configurado baseado no LLMProviderConfig"""
            provider = self.llm_config.name

            if provider == "openai":
                return ChatOpenAI(
                    model=self.llm_config.model,
                    temperature=self.llm_config.temperature,
                    max_tokens=self.llm_config.max_tokens,
                    top_p=self.llm_config.top_p,
                    presence_penalty=self.llm_config.presence_penalty,
                    frequency_penalty=self.llm_config.frequency_penalty,
                    openai_api_key=getattr(settings, 'OPENAI_API_KEY', '')
                )
            elif provider == "anthropic":
                return ChatAnthropic(
                    model=self.llm_config.model,
                    temperature=self.llm_config.temperature,
                    max_tokens=self.llm_config.max_tokens,
                    top_p=self.llm_config.top_p,
                    anthropic_api_key=getattr(settings, 'ANTHROPIC_API_KEY', '')
                )
            elif provider == "google":
                return ChatGoogleGenerativeAI(
                    model=self.llm_config.model,
                    temperature=self.llm_config.temperature,
                    max_output_tokens=self.llm_config.max_tokens,
                    top_p=self.llm_config.top_p,
                    google_api_key=getattr(settings, 'GOOGLE_API_KEY', '')
                )
            else:
                # Fallback para OpenAI se provider não reconhecido
                return ChatOpenAI(
                    model=self.llm_config.model,
                    temperature=self.llm_config.temperature,
                    max_tokens=self.llm_config.max_tokens,
                    openai_api_key=getattr(settings, 'OPENAI_API_KEY', '')
                )

        def get_instructions(self):
            """Retorna instruções dinâmicas com contexto atual"""
            current_time = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            base_instructions = self.instructions

            # Adicionar contexto de arquivos
            context_files_content = self._get_context_files_content()
            if context_files_content:
                base_instructions += f"\n\n=== CONTEXTO ADICIONAL ===\n{context_files_content}"

            return f"{base_instructions}\n\nData e hora atual: {current_time}"

        def _get_context_files_content(self):
            """
            Busca e retorna o conteúdo dos arquivos de contexto ativos
            """
            try:
                context_files = AssistantContextFile.objects.filter(
                    llm_config=self.llm_config,
                    is_active=True,
                    status='ready'
                ).exclude(file_type='pdf').order_by('name')

                if not context_files.exists():
                    return ""

                context_content = []
                total_chars = 0
                max_context_length = 20000

                for file in context_files:
                    if file.extracted_content:
                        file_content = file.extracted_content.strip()

                        if total_chars + len(file_content) > max_context_length:
                            remaining_chars = max_context_length - total_chars
                            if remaining_chars > 100:
                                file_content = file_content[:remaining_chars] + "..."
                                context_content.append(f"**{file.name}:**\n{file_content}")
                            break

                        context_content.append(f"**{file.name}:**\n{file_content}")
                        total_chars += len(file_content) + len(file.name) + 10

                if context_content:
                    result = "\n\n".join(context_content)
                    result += f"\n\n(Contexto baseado em {len(context_content)} arquivo(s) de referência)"
                    return result

                return ""

            except Exception as e:
                print(f"Erro ao buscar arquivos de contexto: {e}")
                return ""

    return DynamicAIAssistant


class DjangoAIAssistantService:
    """
    Service que integra LLMProviderConfig com django-ai-assistant
    """

    def __init__(self, llm_config: LLMProviderConfig, assistant_id: str = None):
        self.llm_config = llm_config
        # Criar uma classe dinâmica AIAssistant
        assistant_class = create_dynamic_assistant_class(llm_config, assistant_id)
        self.assistant = assistant_class()

    def get_llm(self):
        """Delegate para o assistant interno"""
        return self.assistant.get_llm()

    def get_instructions(self):
        """Delegate para o assistant interno"""
        return self.assistant.get_instructions()

class AgentLLMService:
    """
    Service principal que gerencia diferentes provedores LLM usando django-ai-assistant
    """

    def __init__(self, llm_config: LLMProviderConfig, user=None):
        self.llm_config = llm_config

        if llm_config.config_type == 'finance' and user:
            from finance.ai_assistants import FinanceAIAssistant
            self.assistant = FinanceAIAssistant(user=user, llm_config=llm_config)
        elif llm_config.config_type == 'calendar' and user:
            from google_calendar.ai_assistants import GoogleCalendarAIAssistant
            self.assistant = GoogleCalendarAIAssistant(user=user, llm_config=llm_config)
        else:
            self.assistant = DjangoAIAssistantService(llm_config)

    def send_text_message(self, message_content: str, chat_session):
        """
        Envia mensagem de texto usando django-ai-assistant com todas as funcionalidades do OpenAIService

        Args:
            message_content (str): Conteúdo da mensagem
            chat_session: Sessão do chat

        Returns:
            dict: Resposta do assistant ou None em caso de erro
        """
        try:
            print(f"Enviando mensagem via AgentLLMService: {message_content}")

            # VERIFICAR STATUS DA SESSÃO - Não responder se não permitir AI
            if hasattr(chat_session, 'allows_ai_response') and not chat_session.allows_ai_response():
                print(f"🚫 FILTRADO: Sessão {chat_session.from_number} não permite resposta do AI (status: {chat_session.status}) - Assistant não irá responder")
                return None

            # Recuperar últimas 10 mensagens da sessão em ordem cronológica
            last_messages = ChatHistory.objects.filter(session_id=chat_session.from_number, closed=False).order_by("created_at")[:10]

            # Montar contexto do sistema com instruções estruturadas
            system_content = self._build_enhanced_system_prompt()

            # PRIMEIRO: Verificar se é uma solicitação relacionada a calendário
            if self.llm_config.config_type == 'calendar':
                system_content += """CONTEXTO IMPORTANTE:
                - Este usuário está enviando mensagens via WhatsApp
                - O número do WhatsApp é: {whatsapp_number}
                - Use sempre este número nas funções que requerem numero_whatsapp
                - Seja direto e objetivo nas respostas
                - Formate as respostas de forma amigável para WhatsApp
                - Se o usuário solicitar criação de eventos, use os dados fornecidos ou peça os dados que faltam
                - Para listar eventos, seja conciso mas informativo
                - Para verificar disponibilidade, seja claro sobre conflitos{history_context}"""

            # SEGUNDO: Verificar se é uma solicitação relacionada a finanças
            if self.llm_config.config_type == 'finance':
                pass
                # finance_response = self._try_finance_assistant(message_content, chat_session, last_messages)
                # if finance_response:
                #     return finance_response

            # system_content = self._build_enhanced_system_prompt()

            #
            # # Adicionar informação sobre PDFs que serão anexados
            # pdf_files = self._get_pdf_files()
            # if pdf_files:
            #     pdf_names = [pdf.name for pdf in pdf_files]
            #     system_content += f"\n\n=== DOCUMENTOS PDF ANEXADOS ===\n"
            #     system_content += f"Os seguintes documentos PDF estão anexados nesta conversa: {', '.join(pdf_names)}\n"
            #     system_content += "Você pode referenciar e analisar o conteúdo destes PDFs diretamente."
            #
            # # Adicionar informação sobre imagens que serão anexadas
            # image_files = self._get_image_files()
            # if image_files:
            #     image_names = [img.name for img in image_files]
            #     system_content += f"\n\n=== IMAGENS ANEXADAS ===\n"
            #     system_content += f"As seguintes imagens estão anexadas nesta conversa: {', '.join(image_names)}\n"
            #     system_content += "Você pode ver e analisar o conteúdo visual destas imagens diretamente."
            #
            # # Adicionar lista de arquivos disponíveis com URLs
            # available_files = self._get_available_files_with_urls()
            # if available_files:
            #     system_content += f"\n\n=== ARQUIVOS DISPONÍVEIS PARA ENVIO ===\n"
            #     system_content += "Os seguintes arquivos estão disponíveis e podem ser enviados usando o formato JSON:\n"
            #     for file_info in available_files:
            #         system_content += f"• **{file_info['name']}**: {file_info['url']}\n"
            #     system_content += "\nPara enviar qualquer um destes arquivos, use o formato JSON com a URL exata listada acima."
            #
            # # Preparar mensagens usando LangChain format
            messages = []

            # Adicionar instruções do sistema
            from langchain.schema import SystemMessage, HumanMessage, AIMessage
            messages.append(SystemMessage(content=system_content))

            # Adicionar histórico de mensagens
            for msg in last_messages:
                # Garante que content e response nunca sejam None
                human_content = msg.message.get("content") or ""
                ai_response = msg.message.get("response") or ""

                if human_content.strip():
                    messages.append(HumanMessage(content=human_content))

                if ai_response.strip():
                    messages.append(AIMessage(content=ai_response))

            # # Preparar conteúdo da mensagem atual (com suporte a imagens)
            # user_message_content = []
            #
            # # Adicionar texto da mensagem
            # if message_content and message_content.strip():
            #     user_message_content.append({
            #         "type": "text",
            #         "text": message_content
            #     })
            #
            # # Para suporte a imagens no LangChain, precisamos usar ChatOpenAI com vision
            # current_message_content = message_content
            #
            # # Se há imagens, precisamos usar um formato especial para o LangChain
            # image_files = self._get_image_files()
            # if image_files:
            #     # Para LangChain, vamos incluir referência às imagens no texto
            #     image_refs = []
            #     for img in image_files:
            #         image_refs.append(f"[IMAGEM ANEXADA: {img.name}]")
            #
            #     if image_refs:
            #         current_message_content += f"\n\nImagens anexadas: {', '.join(image_refs)}"
            #
            # # Adicionar mensagem atual
            # if current_message_content and current_message_content.strip():
            #     messages.append(HumanMessage(content=current_message_content))

            # Criar histórico da mensagem humana
            history = ChatHistory.create(
                session_id=chat_session.from_number,
                content=message_content,
                external_id=chat_session.id,
                response=None
            )

            # Adicionar mensagem atual ao histórico de mensagens
            messages.append(HumanMessage(content=message_content))

            # Usar django-ai-assistant com suporte a tools
            # O .invoke() do grafo executa com tool calling e histórico manual
            # thread_id=None evita salvar thread no banco
            graph = self.assistant.as_graph(thread_id=None)

            # Configurar limite de recursão e desabilitar salvamento
            config = {
                "recursion_limit": 50,
                "configurable": {
                    "thread_id": None,  # Não salvar thread
                }
            }

            result = graph.invoke({"messages": messages, "input": None}, config=config)
            ai_response = result.get("output", "")

            # Debug: verificar se há tool calls na resposta
            if result.get("messages"):
                last_msg = result["messages"][-1]


            # Salvar resposta no histórico
            history.message['response'] = ai_response
            history.save()

            return ai_response

        except Exception as e:
            print(f"Erro ao comunicar via django-ai-assistant: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    # Manter método send_message para compatibilidade
    def send_message(self, message_content: str, chat_session, context_data: dict = None):
        """Método de compatibilidade que chama send_text_message"""
        return self.send_text_message(message_content, chat_session)

    def _build_message_history(self, chat_session, current_message):
        """
        Constrói histórico de mensagens no formato LangChain
        """
        messages = []

        # Adicionar instruções do sistema
        system_instructions = self.assistant.get_instructions()
        if system_instructions:
            messages.append(SystemMessage(content=system_instructions))

        # Recuperar últimas mensagens da sessão
        last_messages = ChatHistory.objects.filter(
            session_id=chat_session.from_number,
            closed=False
        ).order_by("created_at")[:10]

        # Adicionar mensagens do histórico
        for msg in last_messages:
            human_content = msg.message.get("content") or ""
            ai_response = msg.message.get("response") or ""

            if human_content.strip():
                messages.append(HumanMessage(content=human_content))

            if ai_response.strip():
                messages.append(AIMessage(content=ai_response))

        # Adicionar mensagem atual
        if current_message and current_message.strip():
            messages.append(HumanMessage(content=current_message))

        return messages

    def _get_context_files_content(self):
        """
        Busca e retorna o conteúdo dos arquivos de contexto ativos
        """
        try:
            context_files = AssistantContextFile.objects.filter(
                llm_config=self.llm_config,
                is_active=True,
                status='ready'
            ).exclude(file_type='pdf').order_by('name')

            if not context_files.exists():
                return ""

            context_content = []
            total_chars = 0
            max_context_length = 20000

            for file in context_files:
                if file.extracted_content:
                    file_content = file.extracted_content.strip()

                    if total_chars + len(file_content) > max_context_length:
                        remaining_chars = max_context_length - total_chars
                        if remaining_chars > 100:
                            file_content = file_content[:remaining_chars] + "..."
                            context_content.append(f"**{file.name}:**\n{file_content}")
                        break

                    context_content.append(f"**{file.name}:**\n{file_content}")
                    total_chars += len(file_content) + len(file.name) + 10

            if context_content:
                result = "\n\n".join(context_content)
                result += f"\n\n(Contexto baseado em {len(context_content)} arquivo(s) de referência)"
                return result

            return ""

        except Exception as e:
            print(f"Erro ao buscar arquivos de contexto: {e}")
            return ""

    @method_tool
    def list_context_files(self) -> str:
        """
        Lista arquivos de contexto disponíveis para o assistant

        Returns:
            String com lista de arquivos de contexto
        """
        try:
            files = AssistantContextFile.objects.filter(
                llm_config=self.llm_config,
                is_active=True,
                status='ready'
            ).order_by('name')

            if not files.exists():
                return "Nenhum arquivo de contexto disponível."

            file_list = ["📁 **Arquivos de Contexto Disponíveis:**\n"]

            for i, file in enumerate(files, 1):
                file_info = f"{i}. **{file.name}** ({file.get_file_type_display()})"
                if file.file_size:
                    file_info += f" - {file.get_file_size_display()}"
                file_list.append(file_info)

            return "\n".join(file_list)

        except Exception as e:
            return f"Erro ao listar arquivos: {str(e)}"

    @method_tool
    def get_llm_config_info(self) -> str:
        """
        Retorna informações sobre a configuração LLM atual

        Returns:
            String com informações da configuração
        """
        try:
            config_info = f"""🤖 **Configuração LLM Atual:**

                            📋 **Nome:** {self.llm_config.display_name}
                            🏭 **Provedor:** {self.llm_config.get_name_display()}
                            🧠 **Modelo:** {self.llm_config.model}
                            🌡️ **Temperatura:** {self.llm_config.temperature}
                            📏 **Max Tokens:** {self.llm_config.max_tokens}
                            🎯 **Top-p:** {self.llm_config.top_p}
                            ⚖️ **Penalidade Presença:** {self.llm_config.presence_penalty}
                            🔄 **Penalidade Frequência:** {self.llm_config.frequency_penalty}
                            📝 **Criado em:** {self.llm_config.created_at.strftime('%d/%m/%Y %H:%M')}"""

            return config_info

        except Exception as e:
            return f"Erro ao obter informações da configuração: {str(e)}"


    def _get_pdf_files(self):
        """
        Busca arquivos PDF de contexto para envio direto ao modelo
        """
        try:
            pdf_files = AssistantContextFile.objects.filter(
                llm_config=self.llm_config,
                is_active=True,
                status='ready',
                file_type='pdf'
            ).order_by('name')

            return list(pdf_files)

        except Exception as e:
            print(f"Erro ao buscar arquivos PDF: {e}")
            return []

    def _get_image_files(self):
        """
        Busca arquivos de imagem de contexto para envio direto ao modelo
        """
        try:
            image_files = AssistantContextFile.objects.filter(
                llm_config=self.llm_config,
                is_active=True,
                status='ready',
                file_type__in=['jpg', 'png', 'gif', 'webp']
            ).order_by('name')

            return list(image_files)

        except Exception as e:
            print(f"Erro ao buscar arquivos de imagem: {e}")
            return []

    def _get_available_files_with_urls(self):
        """
        Busca todos os arquivos de contexto ativos e suas URLs para envio
        """
        try:
            # Buscar todos os arquivos de contexto ativos e prontos
            all_files = AssistantContextFile.objects.filter(
                llm_config=self.llm_config,
                is_active=True,
                status='ready'
            ).order_by('name')

            available_files = []

            for file in all_files:
                file_info = {
                    'name': file.name,
                    'type': file.file_type,
                }

                # Tentar obter URL do arquivo
                try:
                    if hasattr(file.file, 'url'):
                        # Se o arquivo tem URL direta (ex: storage público)
                        file_url = file.file.url

                        # Converter URL relativa em absoluta se necessário
                        if file_url.startswith('/'):
                            # Construir URL absoluta usando settings
                            from django.conf import settings
                            base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
                            file_url = f"{base_url.rstrip('/')}{file_url}"

                        file_info['url'] = file_url
                        available_files.append(file_info)

                    elif hasattr(file.file, 'path'):
                        # Se só tem caminho local, criar URL baseada no Django MEDIA_URL
                        from django.conf import settings

                        # Obter o caminho relativo do arquivo
                        full_path = file.file.path
                        media_root = getattr(settings, 'MEDIA_ROOT', '')

                        if media_root and full_path.startswith(media_root):
                            relative_path = full_path[len(media_root):].lstrip('/')
                            media_url = getattr(settings, 'MEDIA_URL', '/media/')

                            # Construir URL completa
                            base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
                            file_url = f"{base_url.rstrip('/')}{media_url.rstrip('/')}/{relative_path}"

                            file_info['url'] = file_url
                            available_files.append(file_info)

                except Exception as url_error:
                    print(f"Erro ao obter URL do arquivo {file.name}: {url_error}")
                    continue

            return available_files

        except Exception as e:
            print(f"Erro ao buscar arquivos disponíveis: {e}")
            return []

    def _process_structured_response(self, ai_response):
        """
        Processa resposta da IA em formato JSON estruturado
        Formato esperado: {"text": "mensagem", "file": "url_do_arquivo"}
        """
        import json
        import re

        try:
            # Tentar encontrar JSON na resposta
            json_pattern = r'\{[^{}]*"text"[^{}]*"file"[^{}]*\}'
            json_match = re.search(json_pattern, ai_response)

            if json_match:
                json_str = json_match.group(0)
                try:
                    parsed_data = json.loads(json_str)

                    # Validar se tem os campos necessários
                    if "text" in parsed_data and "file" in parsed_data:
                        text = parsed_data.get("text", "").strip()
                        file_url = parsed_data.get("file", "").strip()

                        # Validar se ao menos um dos campos não está vazio
                        if text or file_url:
                            result = {
                                "type": "structured",
                                "text": text,
                                "file": file_url
                            }
                            print(f"Resposta estruturada detectada: texto='{text[:50]}...', arquivo='{file_url}'")
                            return result

                except json.JSONDecodeError:
                    pass

            # Tentar formato mais flexível sem JSON estrito
            text_match = re.search(r'"?text"?\s*:\s*"([^"]*)"', ai_response)
            file_match = re.search(r'"?file"?\s*:\s*"([^"]*)"', ai_response)

            if text_match or file_match:
                text = text_match.group(1) if text_match else ""
                file_url = file_match.group(1) if file_match else ""

                if text or file_url:
                    result = {
                        "type": "structured",
                        "text": text.strip(),
                        "file": file_url.strip()
                    }
                    print(f"Resposta estruturada (flexível) detectada: texto='{text[:50]}...', arquivo='{file_url}'")
                    return result

            return None

        except Exception as e:
            print(f"Erro ao processar resposta estruturada: {e}")
            return None

    def _build_enhanced_system_prompt(self):
        """
        Constrói um prompt de sistema melhorado que interpreta melhor as instruções do usuário
        """
        current_time = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

        # Começar com seção de identidade e contexto temporal
        system_prompt = f"=== CONTEXTO E IDENTIDADE ===\n"
        system_prompt += f"Data e hora atual: {current_time}\n\n"

        # Processar e estruturar as instruções do usuário
        enhanced_instructions = self.llm_config.instructions or "Você é um assistente inteligente."

        return enhanced_instructions

    def _enhance_user_instructions(self, raw_instructions):
        """
        Analisa e melhora as instruções fornecidas pelo usuário para torná-las mais efetivas
        """
        instructions = raw_instructions.strip()

        # Detectar padrões comuns e adicionar estrutura
        enhanced = ""

        # Se as instruções contêm características de personalidade
        if any(keyword in instructions.lower() for keyword in ['você é', 'atue como', 'comporte-se', 'seja', 'comportamento']):
            enhanced += "IDENTIDADE E PERSONALIDADE:\n"
            enhanced += f"{instructions}\n\n"

            enhanced += "APLICAÇÃO DAS INSTRUÇÕES:\n"
            enhanced += "• Mantenha essa identidade consistentemente durante toda a conversa\n"
            enhanced += "• Todas as suas respostas devem refletir essa personalidade\n"
            enhanced += "• Se houver conflito entre instruções, priorize o comportamento descrito acima\n"

        # Se as instruções contêm procedimentos ou regras específicas
        elif any(keyword in instructions.lower() for keyword in ['sempre', 'nunca', 'quando', 'se', 'deve', 'não deve', 'regra', 'procedimento']):
            enhanced += "REGRAS E PROCEDIMENTOS:\n"
            enhanced += f"{instructions}\n\n"

            enhanced += "CUMPRIMENTO DAS REGRAS:\n"
            enhanced += "• Siga rigorosamente todas as regras listadas acima\n"
            enhanced += "• Verifique cada resposta antes de enviá-la para garantir conformidade\n"
            enhanced += "• Em caso de dúvida, peça esclarecimentos ao usuário\n"

        # Se as instruções contêm conhecimento específico ou especialização
        elif any(keyword in instructions.lower() for keyword in ['especialista', 'conhecimento', 'área', 'domínio', 'expert', 'foco']):
            enhanced += "ÁREA DE ESPECIALIZAÇÃO:\n"
            enhanced += f"{instructions}\n\n"

            enhanced += "APLICAÇÃO DO CONHECIMENTO ESPECIALIZADO:\n"
            enhanced += "• Use seu conhecimento especializado para fornecer respostas detalhadas e precisas\n"
            enhanced += "• Cite fontes ou referências quando apropriado\n"
            enhanced += "• Explique conceitos complexos de forma acessível quando necessário\n"

        # Caso geral - instruções simples ou outras
        else:
            enhanced += "INSTRUÇÕES PERSONALIZADAS:\n"
            enhanced += f"{instructions}\n\n"

            enhanced += "INTERPRETAÇÃO E APLICAÇÃO:\n"
            enhanced += "• Interprete essas instruções de forma ampla e consistente\n"
            enhanced += "• Aplique o espírito das instruções, não apenas a letra\n"
            enhanced += "• Adapte sua abordagem conforme necessário para cumprir os objetivos\n"

        # Adicionar lembretes importantes
        enhanced += "\nLEMBRETE IMPORTANTE:\n"
        enhanced += "Estas instruções têm prioridade sobre comportamentos padrão. Certifique-se de que cada resposta está alinhada com as diretrizes acima."

        return enhanced




# Factory function para criar services baseados no provider
def create_llm_service(llm_config: LLMProviderConfig, user=None):
    """
    Factory function para criar o service apropriado baseado na configuração LLM

    Args:
        llm_config: Configuração do LLM
        use_django_ai_assistant: Se deve usar django-ai-assistant (padrão: True)
        user: Usuário para assistentes especializados (finance, calendar)

    Returns:
        Service instance apropriado
    """
    return AgentLLMService(user=user, llm_config=llm_config)
