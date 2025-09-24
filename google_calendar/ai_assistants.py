import traceback
from django.utils import timezone
from django_ai_assistant import AIAssistant, method_tool
from datetime import datetime, timedelta
from .services import GoogleCalendarService


class GoogleCalendarAIAssistant(AIAssistant):
    id = "google_calendar_assistant"
    name = "Assistente de Google Calendar"
    instructions = """Você é um assistente inteligente especializado em Google Calendar.

    Você pode ajudar os usuários a:
    - Listar eventos da agenda
    - Criar novos eventos
    - Verificar disponibilidade
    - Gerenciar a agenda

    Sempre seja útil, preciso e forneça informações detalhadas sobre os eventos.
    Use as ferramentas disponíveis para acessar e modificar o Google Calendar do usuário.

    Quando listar eventos, formate as informações de forma clara e legível.
    Quando criar eventos, confirme os detalhes com o usuário antes de criar.
    
    Ao solicitar criar evento não necessita pedir confirmação, epenas crie o evento.
    Para limpar a agenda de uma data específica, utilize listar_eventos_calendar para obter os eventos e, em seguida, delete todos os eventos daquele dia    """
    model = "gpt-4o-mini"

    def get_instructions(self):
        return f"{self.instructions}\n\nData e hora atual: {timezone.now().strftime('%d/%m/%Y %H:%M')}"

    @method_tool
    def listar_eventos_calendar(self, numero_whatsapp: str, max_resultados: int = 10) -> str:
        """Lista os próximos eventos do Google Calendar do usuário

        Args:
            numero_whatsapp: Número do WhatsApp do usuário
            max_resultados: Número máximo de eventos para retornar (padrão: 10)

        Returns:
            String com os eventos formatados ou mensagem de erro
        """
        try:
            calendar_service = GoogleCalendarService()
            success, events = calendar_service.list_events(numero_whatsapp, max_results=max_resultados)

            if not success:
                return f"❌ Erro ao acessar o calendário: {events}"

            if not events:
                return "📅 Você não tem eventos próximos na sua agenda."

            eventos_formatados = ["📅 *Seus Próximos Eventos:*\n"]

            for i, event in enumerate(events, 1):
                start = event['start'].get('dateTime', event['start'].get('date'))
                title = event.get('summary', 'Evento sem título')
                location = event.get('location', '')
                description = event.get('description', '')

                # Formatar data/hora
                if 'T' in start:  # É datetime
                    dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    formatted_time = dt.strftime('%d/%m/%Y às %H:%M')
                else:  # É só data
                    dt = datetime.fromisoformat(start)
                    formatted_time = dt.strftime('%d/%m/%Y (dia todo)')

                evento_info = f"{i}. *{title}*\n   📅 {formatted_time}"

                if location:
                    evento_info += f"\n   📍 {location}"

                if description and len(description) < 100:
                    evento_info += f"\n   📝 {description}"

                eventos_formatados.append(evento_info)

            return "\n\n".join(eventos_formatados)

        except Exception as e:
            return f"❌ Erro interno ao listar eventos: {str(e)}"

    @method_tool
    def criar_evento_calendar(
        self,
        numero_whatsapp: str,
        titulo: str,
        data_inicio: str,
        hora_inicio: str = "",
        data_fim: str = "",
        hora_fim: str = "",
        descricao: str = "",
        localizacao: str = ""
    ) -> str:
        """Cria um novo evento no Google Calendar do usuário

        Args:
            numero_whatsapp: Número do WhatsApp do usuário
            titulo: Título do evento
            data_inicio: Data de início no formato DD/MM/YYYY
            hora_inicio: Hora de início no formato HH:MM (opcional, se vazio será evento de dia inteiro)
            data_fim: Data de fim no formato DD/MM/YYYY (opcional, usa data_inicio se vazio)
            hora_fim: Hora de fim no formato HH:MM (opcional, usa hora_inicio + 1 hora se vazio)
            descricao: Descrição do evento (opcional)
            localizacao: Local do evento (opcional)

        Returns:
            String com confirmação de criação ou mensagem de erro
        """
        try:
            # Processa as datas
            try:
                data_inicio_obj = datetime.strptime(data_inicio, '%d/%m/%Y')
            except ValueError:
                return "❌ Formato de data inválido. Use DD/MM/YYYY (ex: 25/12/2024)"

            # Define data de fim se não fornecida
            if not data_fim:
                data_fim_obj = data_inicio_obj
            else:
                try:
                    data_fim_obj = datetime.strptime(data_fim, '%d/%m/%Y')
                except ValueError:
                    return "❌ Formato de data de fim inválido. Use DD/MM/YYYY"

            # Prepara os dados do evento
            event_data = {
                'summary': titulo,
                'description': f"Evento criado via WhatsApp\n\n{descricao}" if descricao else "Evento criado via WhatsApp"
            }

            if localizacao:
                event_data['location'] = localizacao

            # Define horário
            if hora_inicio:
                try:
                    hora_inicio_obj = datetime.strptime(hora_inicio, '%H:%M').time()
                    start_datetime = datetime.combine(data_inicio_obj.date(), hora_inicio_obj)

                    # Define hora de fim
                    if hora_fim:
                        hora_fim_obj = datetime.strptime(hora_fim, '%H:%M').time()
                        end_datetime = datetime.combine(data_fim_obj.date(), hora_fim_obj)
                    else:
                        # 1 hora de duração por padrão
                        end_datetime = start_datetime + timedelta(hours=1)

                    event_data['start'] = {
                        'dateTime': start_datetime.isoformat(),
                        'timeZone': 'America/Sao_Paulo',
                    }
                    event_data['end'] = {
                        'dateTime': end_datetime.isoformat(),
                        'timeZone': 'America/Sao_Paulo',
                    }

                except ValueError:
                    return "❌ Formato de hora inválido. Use HH:MM (ex: 14:30)"
            else:
                # Evento de dia inteiro
                event_data['start'] = {
                    'date': data_inicio_obj.strftime('%Y-%m-%d'),
                }
                # Para eventos de dia inteiro, a data de fim deve ser o dia seguinte
                event_data['end'] = {
                    'date': (data_fim_obj + timedelta(days=1)).strftime('%Y-%m-%d'),
                }

            # Cria o evento
            calendar_service = GoogleCalendarService()
            success, result = calendar_service.create_event(numero_whatsapp, event_data)

            if success:
                # Formata informações do evento criado
                data_formatada = data_inicio_obj.strftime('%d/%m/%Y')

                resposta = f"""✅ *Evento criado com sucesso!*

📋 *Título:* {titulo}
📅 *Data:* {data_formatada}"""

                if hora_inicio:
                    resposta += f"\n⏰ *Horário:* {hora_inicio}"
                    if hora_fim:
                        resposta += f" às {hora_fim}"
                    else:
                        hora_fim_calc = (datetime.strptime(hora_inicio, '%H:%M') + timedelta(hours=1)).strftime('%H:%M')
                        resposta += f" às {hora_fim_calc}"
                else:
                    resposta += f"\n⏰ *Tipo:* Dia inteiro"

                if localizacao:
                    resposta += f"\n📍 *Local:* {localizacao}"

                if descricao:
                    resposta += f"\n📝 *Descrição:* {descricao}"

                # Extrai link se disponível
                if ': ' in result:
                    link = result.split(': ')[-1]
                    resposta += f"\n\n🔗 *Ver no Google Calendar:* {link}"

                return resposta
            else:
                return f"❌ Erro ao criar evento: {result}"

        except Exception as e:
            return f"❌ Erro interno ao criar evento: {str(e)}"

    @method_tool
    def verificar_disponibilidade(self, numero_whatsapp: str, data: str, hora_inicio: str = "", hora_fim: str = "") -> str:
        """Verifica se o usuário está disponível em uma determinada data/hora

        Args:
            numero_whatsapp: Número do WhatsApp do usuário
            data: Data para verificar no formato DD/MM/YYYY
            hora_inicio: Hora de início no formato HH:MM (opcional)
            hora_fim: Hora de fim no formato HH:MM (opcional)

        Returns:
            String com informação sobre disponibilidade
        """
        try:
            # Lista eventos do dia
            calendar_service = GoogleCalendarService()
            success, events = calendar_service.list_events(numero_whatsapp, max_results=50)

            if not success:
                return f"❌ Erro ao verificar disponibilidade: {events}"

            # Converte a data fornecida
            try:
                data_obj = datetime.strptime(data, '%d/%m/%Y')
            except ValueError:
                return "❌ Formato de data inválido. Use DD/MM/YYYY"

            # Filtra eventos do dia especificado
            eventos_do_dia = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                if 'T' in start:  # É datetime
                    event_date = datetime.fromisoformat(start.replace('Z', '+00:00')).date()
                else:  # É só data
                    event_date = datetime.fromisoformat(start).date()

                if event_date == data_obj.date():
                    eventos_do_dia.append(event)

            resposta = f"📅 *Disponibilidade para {data_obj.strftime('%d/%m/%Y')}:*\n\n"

            if not eventos_do_dia:
                resposta += "✅ Você está completamente livre neste dia!"
            else:
                resposta += f"📋 *Você tem {len(eventos_do_dia)} evento(s) neste dia:*\n\n"

                for i, event in enumerate(eventos_do_dia, 1):
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    title = event.get('summary', 'Evento sem título')

                    if 'T' in start:  # É datetime
                        dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                        time_str = dt.strftime('%H:%M')

                        # Verifica se há conflito com horário solicitado
                        if hora_inicio and hora_fim:
                            try:
                                hora_inicio_obj = datetime.strptime(hora_inicio, '%H:%M').time()
                                hora_fim_obj = datetime.strptime(hora_fim, '%H:%M').time()

                                event_start_time = dt.time()
                                # Simplificada - apenas verifica sobreposição básica
                                if (hora_inicio_obj <= event_start_time <= hora_fim_obj):
                                    resposta += f"{i}. ⚠️ *{title}* às {time_str} (CONFLITO!)\n"
                                else:
                                    resposta += f"{i}. *{title}* às {time_str}\n"
                            except ValueError:
                                resposta += f"{i}. *{title}* às {time_str}\n"
                        else:
                            resposta += f"{i}. *{title}* às {time_str}\n"
                    else:  # Dia inteiro
                        resposta += f"{i}. *{title}* (dia inteiro)\n"

                # Verifica disponibilidade específica se horário foi fornecido
                if hora_inicio and not hora_fim:
                    resposta += f"\n💡 *Para criar um evento às {hora_inicio}, verifique se não há conflitos acima.*"
                elif hora_inicio and hora_fim:
                    resposta += f"\n💡 *Para o período {hora_inicio}-{hora_fim}, verifique se não há conflitos marcados acima.*"

            return resposta

        except Exception as e:
            return f"❌ Erro interno ao verificar disponibilidade: {str(e)}"

    @method_tool
    def deletar_evento(self, numero_whatsapp: str, titulo: str = "", hora: str = "", data: str = "") -> str:
        """Deleta um evento do Google Calendar pelo título ou pela hora

        Args:
            numero_whatsapp: Número do WhatsApp do usuário
            titulo: Título do evento (opcional)
            hora: Hora no formato HH:MM (opcional)
            data: Data no formato DD/MM/YYYY (opcional, usado com hora)

        Returns:
            String com resultado da operação
        """
        try:
            calendar_service = GoogleCalendarService()
            success, events = calendar_service.list_events(numero_whatsapp, max_results=50)

            if not success:
                return f"❌ Erro ao buscar eventos: {events}"

            candidato = None

            # Normaliza inputs
            titulo = titulo.strip().lower() if titulo else ""
            hora = hora.strip() if hora else ""

            for event in events:
                event_title = event.get("summary", "").lower()
                start = event["start"].get("dateTime", event["start"].get("date"))

                # Caso 1: deletar pelo título
                if titulo and titulo in event_title:
                    candidato = event
                    break

                # Caso 2: deletar pela hora (se data for fornecida também, restringe mais)
                if hora and "T" in start:
                    dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    time_str = dt.strftime("%H:%M")

                    if time_str == hora:
                        if data:
                            data_obj = datetime.strptime(data, "%d/%m/%Y").date()
                            if dt.date() == data_obj:
                                candidato = event
                                break
                        else:
                            candidato = event
                            break

            if not candidato:
                return "😕 Não encontrei nenhum evento com esses critérios."

            # Deleta o evento encontrado
            service = calendar_service.get_calendar_service(numero_whatsapp)
            service.events().delete(calendarId="primary", eventId=candidato["id"]).execute()

            return f"🗑️ Evento *{candidato.get('summary', 'Sem título')}* deletado com sucesso!"
        except Exception as e:
            traceback.print_exc()
            return f"❌ Erro ao deletar evento: {str(e)}"