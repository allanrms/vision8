from django.utils import timezone
from django.conf import settings
from django.db import models
from django_ai_assistant import AIAssistant, method_tool
from datetime import datetime, timedelta
from decimal import Decimal
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from .models import Category, Movement, PaymentMethod

"""Você é um assistente inteligente especializado em gestão financeira.

    Você pode ajudar os usuários a:
    - Registrar receitas e despesas
    - Listar movimentações financeiras
    - Verificar saldo por categoria
    - Criar e gerenciar categorias
    - Analisar gastos por período
    - Gerenciar métodos de pagamento para despesas

    Sempre seja útil, preciso e forneça informações claras sobre as finanças.
    Use as ferramentas disponíveis para registrar e consultar movimentações financeiras.

    IMPORTANTE: Quando usar qualquer ferramenta, retorne EXATAMENTE a resposta da ferramenta, sem adicionar, modificar ou reformular.
    As ferramentas já retornam mensagens formatadas e completas.

    Para valores monetários, sempre use o formato brasileiro (R$ 100,50).
    Ao registrar uma movimentação, não é necessário pedir confirmação, apenas registre.
    Analise e insira na categoria que faça mais sentido.

    Para despesas, sempre especifique o método de pagamento (PIX, Dinheiro, Cartão, etc.).
    Se não especificado, use "Não especificado" como padrão para despesas."""

class FinanceAIAssistant(AIAssistant):
    id = "finance_assistant"
    name = "Assistente de Finanças"
    instructions = ""
    model = "gpt-4o-mini"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._user = kwargs.get('user')
        self._llm_config = kwargs.get('llm_config')

        # Sobrescrever configurações se llm_config for fornecido
        if self._llm_config:
            self.name = self._llm_config.display_name or "Assistente de Finanças"
            self.model = self._llm_config.model
            if self._llm_config.instructions:
                self.instructions = self._llm_config.instructions

    def get_instructions(self):
        base_instructions = f"{self.instructions}\n\nData e hora atual: {timezone.now().strftime('%d/%m/%Y %H:%M')}"

        # Adicionar lista de categorias disponíveis do usuário
        if self._user:
            categories = Category.objects.filter(user=self._user, is_active=True).order_by('name')
            if categories.exists():
                categorias_lista = "\n".join([f"  - {cat.name}" for cat in categories])
                base_instructions += f"\n\n**CATEGORIAS DISPONÍVEIS DO USUÁRIO:**\n{categorias_lista}\n\nIMPORTANTE: Use EXATAMENTE um desses nomes de categoria ao registrar movimentações. Escolha a categoria que melhor se encaixa na descrição da movimentação."

            # Adicionar lista de métodos de pagamento disponíveis
            payment_methods = PaymentMethod.objects.filter(
                models.Q(user=self._user) | models.Q(user__isnull=True),
                is_active=True
            ).order_by('name')

            if payment_methods.exists():
                metodos_lista = "\n".join([f"  - {method.name}" for method in payment_methods])
                base_instructions += f"\n\n**MÉTODOS DE PAGAMENTO DISPONÍVEIS:**\n{metodos_lista}\n\nIMPORTANTE: Para despesas, sempre especifique o método de pagamento usando EXATAMENTE um desses nomes. Se não especificado, use 'Não especificado' como padrão."

        return base_instructions

    def get_llm(self):
        if not self._llm_config:
            return super().get_llm()

        provider = self._llm_config.name

        if provider == "openai":
            return ChatOpenAI(
                model=self._llm_config.model,
                temperature=self._llm_config.temperature,
                max_tokens=self._llm_config.max_tokens,
                top_p=self._llm_config.top_p,
                presence_penalty=self._llm_config.presence_penalty,
                frequency_penalty=self._llm_config.frequency_penalty,
                openai_api_key=getattr(settings, 'OPENAI_API_KEY', '')
            )
        elif provider == "anthropic":
            return ChatAnthropic(
                model=self._llm_config.model,
                temperature=self._llm_config.temperature,
                max_tokens=self._llm_config.max_tokens,
                top_p=self._llm_config.top_p,
                anthropic_api_key=getattr(settings, 'ANTHROPIC_API_KEY', '')
            )
        elif provider == "google":
            return ChatGoogleGenerativeAI(
                model=self._llm_config.model,
                temperature=self._llm_config.temperature,
                max_output_tokens=self._llm_config.max_tokens,
                top_p=self._llm_config.top_p,
                google_api_key=getattr(settings, 'GOOGLE_API_KEY', '')
            )
        else:
            return ChatOpenAI(
                model=self._llm_config.model,
                temperature=self._llm_config.temperature,
                max_tokens=self._llm_config.max_tokens,
                openai_api_key=getattr(settings, 'OPENAI_API_KEY', '')
            )

    @method_tool
    def listar_movimentacoes(self, limite: int = 500, tipo: str = "", categoria: str = "", data_inicial: str = "", data_final: str = "") -> str:
        """Lista as movimentações financeiras

        Args:
            limite: Número máximo de movimentações para retornar (padrão: 10)
            tipo: Filtro por tipo ('income' para receitas, 'expense' para despesas, vazio para todos)
            categoria: Nome da categoria para filtrar (opcional)
            data_inicial: Data inicial no formato DD/MM/YYYY (opcional)
            data_final: Data final no formato DD/MM/YYYY (opcional)

        Returns:
            String com as movimentações formatadas ou mensagem de erro
        """
        try:
            user = self._user
            queryset = Movement.objects.filter(user=user)

            # Aplicar filtros
            if tipo in ['income', 'expense']:
                queryset = queryset.filter(type=tipo)

            if categoria:
                queryset = queryset.filter(category__name__icontains=categoria)

            # Filtrar por período (data do movimento, não data de criação)
            print(f'data_inicial: {data_inicial}')
            if data_inicial:
                try:
                    data_inicio = datetime.strptime(data_inicial, '%d/%m/%Y').date()
                    queryset = queryset.filter(date__gte=data_inicio)
                except ValueError:
                    return "❌ Formato de data inicial inválido. Use DD/MM/YYYY (ex: 25/12/2024)"

            print(f'data_final: {data_final}')
            if data_final:
                try:
                    data_fim = datetime.strptime(data_final, '%d/%m/%Y').date()
                    queryset = queryset.filter(date__lte=data_fim)
                except ValueError:
                    return "❌ Formato de data final inválido. Use DD/MM/YYYY (ex: 25/12/2024)"

            movements = queryset.order_by('-date', '-created_at')[:limite]

            if not movements:
                return "💰 Você ainda não tem movimentações registradas."

            movimentacoes_formatadas = ["💰 *Suas Movimentações:*\n"]

            total_receitas = sum(m.amount for m in movements if m.type == 'income')
            total_despesas = sum(m.amount for m in movements if m.type == 'expense')
            saldo = total_receitas - total_despesas

            for i, movement in enumerate(movements, 1):
                tipo_icon = "📈" if movement.type == 'income' else "📉"
                sinal = "+" if movement.type == 'income' else "-"
                cor = "🟢" if movement.type == 'income' else "🔴"

                data_formatada = movement.date.strftime('%d/%m/%Y')

                movimento_info = f"{i}. {tipo_icon} *{movement.description}*\n"
                movimento_info += f"   {cor} {sinal}R$ {movement.amount:.2f}\n"
                movimento_info += f"   📅 {data_formatada}\n"
                movimento_info += f"   🏷️ {movement.category.name}"

                # Adicionar método de pagamento se for despesa
                if movement.type == 'expense' and movement.payment_method:
                    movimento_info += f"\n   💳 {movement.payment_method.name}"

                movimentacoes_formatadas.append(movimento_info)

            resultado = "\n\n".join(movimentacoes_formatadas)

            # Adicionar resumo
            resultado += f"\n\n📊 *Resumo do período:*\n"
            resultado += f"📈 Receitas: R$ {total_receitas:.2f}\n"
            resultado += f"📉 Despesas: R$ {total_despesas:.2f}\n"
            resultado += f"💰 Saldo: R$ {saldo:.2f}"

            return resultado

        except Exception as e:
            return f"❌ Erro interno ao listar movimentações: {str(e)}"

    @method_tool
    def registrar_movimentacao(
        self,
        tipo: str,
        valor: float,
        descricao: str,
        categoria: str,
        data: str = "",
        metodo_pagamento: str = ""
    ) -> str:
        """Registra uma nova movimentação financeira

        Args:
            tipo: Tipo da movimentação ('income' para receita, 'expense' para despesa)
            valor: Valor da movimentação (sempre positivo)
            descricao: Descrição da movimentação
            categoria: Nome da categoria
            data: Data no formato DD/MM/YYYY (opcional, usa data atual se vazio)
            metodo_pagamento: Método de pagamento (obrigatório para despesas, opcional para receitas)

        Returns:
            String com confirmação de registro ou mensagem de erro
        """
        try:
            # Validar tipo
            if tipo not in ['income', 'expense']:
                return "❌ Tipo inválido. Use 'income' para receita ou 'expense' para despesa."

            # Validar valor
            if valor <= 0:
                return "❌ O valor deve ser maior que zero."

            valor_decimal = Decimal(str(valor))

            # Processar data
            if data:
                try:
                    data_obj = datetime.strptime(data, '%d/%m/%Y').date()
                except ValueError:
                    return "❌ Formato de data inválido. Use DD/MM/YYYY (ex: 25/12/2024)"
            else:
                data_obj = timezone.now().date()

            user = self._user

            category = Category.objects.filter(user=user, name__iexact=categoria, is_active=True).first()

            if not category:
                available_categories = Category.objects.filter(user=user, is_active=True).values_list('name', flat=True)
                if not available_categories:
                    return "❌ Você ainda não possui categorias cadastradas."

                categories_list = "\n".join([f"  - {cat}" for cat in available_categories])
                return f"❌ Categoria '{categoria}' não encontrada. Use EXATAMENTE um dos nomes disponíveis:\n\n{categories_list}"

            # Processar método de pagamento para despesas
            payment_method = None
            if tipo == 'expense':
                if not metodo_pagamento:
                    # Usar "Não especificado" como padrão se não informado
                    metodo_pagamento = "Não especificado"

                payment_method = PaymentMethod.objects.filter(
                    models.Q(user=user) | models.Q(user__isnull=True),
                    name__iexact=metodo_pagamento,
                    is_active=True
                ).first()

                if not payment_method:
                    available_methods = PaymentMethod.objects.filter(
                        models.Q(user=user) | models.Q(user__isnull=True),
                        is_active=True
                    ).values_list('name', flat=True)

                    methods_list = "\n".join([f"  - {method}" for method in available_methods])
                    return f"❌ Método de pagamento '{metodo_pagamento}' não encontrado. Use EXATAMENTE um dos nomes disponíveis:\n\n{methods_list}"

            Movement.objects.create(
                user=user,
                type=tipo,
                amount=valor_decimal,
                description=descricao,
                date=data_obj,
                category=category,
                payment_method=payment_method
            )

            tipo_display = "Receita" if tipo == 'income' else "Despesa"
            tipo_icon = "📈" if tipo == 'income' else "📉"
            sinal = "+" if tipo == 'income' else "-"
            cor = "🟢" if tipo == 'income' else "🔴"

            resposta = f"""✅ *{tipo_display} registrada com sucesso!*

{tipo_icon} *Descrição:* {descricao}
{cor} *Valor:* {sinal}R$ {valor:.2f}
📅 *Data:* {data_obj.strftime('%d/%m/%Y')}
🏷️ *Categoria:* {category.name}"""

            # Adicionar método de pagamento se for despesa
            if payment_method:
                resposta += f"\n💳 *Método de Pagamento:* {payment_method.name}"

            return resposta

        except Exception as e:
            return f"❌ Erro interno ao registrar movimentação: {str(e)}"

    @method_tool
    def saldo_por_categoria(self, periodo_dias: int = 30) -> str:
        """Mostra o saldo por categoria nos últimos dias

        Args:
            periodo_dias: Número de dias para considerar (padrão: 30)

        Returns:
            String com saldo por categoria formatado
        """
        try:
            user = self._user
            data_inicio = timezone.now().date() - timedelta(days=periodo_dias)

            movements = Movement.objects.filter(user=user, date__gte=data_inicio)

            if not movements:
                return f"💰 Não há movimentações nos últimos {periodo_dias} dias."

            # Agrupar por categoria
            categorias = {}
            for movement in movements:
                categoria_nome = movement.category.name
                if categoria_nome not in categorias:
                    categorias[categoria_nome] = {
                        'receitas': Decimal('0'),
                        'despesas': Decimal('0'),
                        'quantidade': 0
                    }

                if movement.type == 'income':
                    categorias[categoria_nome]['receitas'] += movement.amount
                else:
                    categorias[categoria_nome]['despesas'] += movement.amount

                categorias[categoria_nome]['quantidade'] += 1

            # Formatar resposta
            resultado = [f"📊 *Saldo por Categoria - Últimos {periodo_dias} dias:*\n"]

            total_receitas = Decimal('0')
            total_despesas = Decimal('0')

            for categoria_nome, dados in sorted(categorias.items()):
                saldo_categoria = dados['receitas'] - dados['despesas']
                total_receitas += dados['receitas']
                total_despesas += dados['despesas']

                cor = "🟢" if saldo_categoria >= 0 else "🔴"
                sinal = "+" if saldo_categoria >= 0 else ""

                categoria_info = f"🏷️ *{categoria_nome}*\n"
                categoria_info += f"   📈 Receitas: R$ {dados['receitas']:.2f}\n"
                categoria_info += f"   📉 Despesas: R$ {dados['despesas']:.2f}\n"
                categoria_info += f"   {cor} Saldo: {sinal}R$ {saldo_categoria:.2f}\n"
                categoria_info += f"   📊 {dados['quantidade']} movimentações"

                resultado.append(categoria_info)

            # Totais
            saldo_total = total_receitas - total_despesas
            cor_total = "🟢" if saldo_total >= 0 else "🔴"
            sinal_total = "+" if saldo_total >= 0 else ""

            resultado.append(f"\n💰 *RESUMO GERAL:*")
            resultado.append(f"📈 Total Receitas: R$ {total_receitas:.2f}")
            resultado.append(f"📉 Total Despesas: R$ {total_despesas:.2f}")
            resultado.append(f"{cor_total} *Saldo Final: {sinal_total}R$ {saldo_total:.2f}*")

            return "\n\n".join(resultado)

        except Exception as e:
            return f"❌ Erro interno ao calcular saldo por categoria: {str(e)}"

    @method_tool
    def listar_categorias(self) -> str:
        """Lista todas as categorias disponíveis

        Returns:
            String com as categorias formatadas
        """
        try:
            user = self._user
            categories = Category.objects.filter(user=user, is_active=True).order_by('name')

            if not categories:
                return "🏷️ Nenhuma categoria encontrada. As categorias são criadas automaticamente quando você registra movimentações."

            resultado = ["🏷️ *Categorias Disponíveis:*\n"]

            for i, category in enumerate(categories, 1):
                # Contar movimentações da categoria
                total_movements = Movement.objects.filter(user=user, category=category).count()

                categoria_info = f"{i}. *{category.name}*"
                if category.description:
                    categoria_info += f"\n   📝 {category.description}"
                categoria_info += f"\n   📊 {total_movements} movimentações"

                resultado.append(categoria_info)

            return "\n\n".join(resultado)

        except Exception as e:
            return f"❌ Erro interno ao listar categorias: {str(e)}"

    @method_tool
    def criar_categoria(self, nome: str, descricao: str = "", cor: str = "#3498db") -> str:
        """Cria uma nova categoria

        Args:
            nome: Nome da categoria
            descricao: Descrição da categoria (opcional)
            cor: Cor da categoria em hexadecimal (opcional, padrão: #3498db)

        Returns:
            String com confirmação de criação ou mensagem de erro
        """
        try:
            user = self._user

            # Verificar se categoria já existe
            if Category.objects.filter(user=user, name__iexact=nome).exists():
                return f"❌ A categoria '{nome}' já existe."

            # Criar categoria
            category = Category.objects.create(
                user=user,
                name=nome,
                description=descricao,
                color=cor
            )

            resposta = f"""✅ *Categoria criada com sucesso!*

🏷️ *Nome:* {nome}"""

            if descricao:
                resposta += f"\n📝 *Descrição:* {descricao}"

            resposta += f"\n🎨 *Cor:* {cor}"

            return resposta

        except Exception as e:
            return f"❌ Erro interno ao criar categoria: {str(e)}"

    @method_tool
    def deletar_categoria(self, nome: str) -> str:
        """Deleta uma categoria existente

        Args:
            nome: Nome da categoria a ser deletada

        Returns:
            String com resultado da operação
        """
        try:
            user = self._user

            # Buscar categoria
            category = Category.objects.filter(user=user, name__icontains=nome).first()

            if not category:
                return f"❌ Categoria '{nome}' não encontrada."

            # Verificar se há movimentações usando esta categoria
            movements_count = Movement.objects.filter(user=user, category=category).count()

            if movements_count > 0:
                return f"❌ Não é possível deletar a categoria '{category.name}' pois ela possui {movements_count} movimentações associadas.\n\n💡 Você pode desativar a categoria ao invés de deletá-la."

            # Deletar categoria
            category_name = category.name
            category.delete()

            return f"🗑️ *Categoria deletada com sucesso!*\n\n🏷️ {category_name}"

        except Exception as e:
            return f"❌ Erro interno ao deletar categoria: {str(e)}"

    @method_tool
    def deletar_movimentacao(self, descricao: str = "", data: str = "", valor: float = 0) -> str:
        """Deleta uma movimentação financeira

        Args:
            descricao: Descrição da movimentação (busca parcial)
            data: Data no formato DD/MM/YYYY (opcional)
            valor: Valor da movimentação (opcional)

        Returns:
            String com resultado da operação
        """
        try:
            user = self._user
            queryset = Movement.objects.filter(user=user)

            # Aplicar filtros
            if descricao:
                queryset = queryset.filter(description__icontains=descricao)

            if data:
                try:
                    data_obj = datetime.strptime(data, '%d/%m/%Y').date()
                    queryset = queryset.filter(date=data_obj)
                except ValueError:
                    return "❌ Formato de data inválido. Use DD/MM/YYYY"

            if valor > 0:
                queryset = queryset.filter(amount=Decimal(str(valor)))

            movements = queryset.order_by('-date', '-created_at')

            if not movements:
                return "😕 Não encontrei nenhuma movimentação com esses critérios."

            if movements.count() > 1:
                # Mostrar opções se houver múltiplas movimentações
                resultado = ["❓ *Encontrei múltiplas movimentações:*\n"]
                for i, movement in enumerate(movements[:5], 1):
                    tipo_icon = "📈" if movement.type == 'income' else "📉"
                    sinal = "+" if movement.type == 'income' else "-"

                    movimento_info = f"{i}. {tipo_icon} {movement.description}\n"
                    movimento_info += f"   {sinal}R$ {movement.amount:.2f} - {movement.date.strftime('%d/%m/%Y')}"

                    resultado.append(movimento_info)

                resultado.append("\n💡 *Seja mais específico nos critérios para deletar apenas uma movimentação.*")
                return "\n\n".join(resultado)

            # Deletar a movimentação encontrada
            movement = movements.first()
            tipo_display = "Receita" if movement.type == 'income' else "Despesa"
            descricao_movimento = movement.description
            valor_movimento = movement.amount
            data_movimento = movement.date.strftime('%d/%m/%Y')

            movement.delete()

            return f"🗑️ *{tipo_display} deletada com sucesso!*\n\n📝 {descricao_movimento}\n💰 R$ {valor_movimento:.2f}\n📅 {data_movimento}"

        except Exception as e:
            return f"❌ Erro interno ao deletar movimentação: {str(e)}"