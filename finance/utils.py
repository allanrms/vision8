"""
Utilitários para o módulo de finanças
"""

# Categorias padrão para uma casa de família
DEFAULT_CATEGORIES = [
    # Moradia
    {
        "name": "Aluguel",
        "icon": "🏠",
        "color": "#e74c3c",
        "description": "Pagamento de aluguel mensal"
    },
    {
        "name": "Condomínio",
        "icon": "🏢",
        "color": "#3498db",
        "description": "Taxa de condomínio"
    },
    {
        "name": "IPTU",
        "icon": "🏛️",
        "color": "#9b59b6",
        "description": "Imposto predial e territorial urbano"
    },
    {
        "name": "Energia Elétrica",
        "icon": "💡",
        "color": "#f39c12",
        "description": "Conta de luz"
    },
    {
        "name": "Água",
        "icon": "💧",
        "color": "#1abc9c",
        "description": "Conta de água"
    },
    {
        "name": "Gás",
        "icon": "🔥",
        "color": "#e67e22",
        "description": "Gás de cozinha ou encanado"
    },
    {
        "name": "Internet",
        "icon": "🌐",
        "color": "#2ecc71",
        "description": "Serviço de internet"
    },
    {
        "name": "Telefone",
        "icon": "📞",
        "color": "#34495e",
        "description": "Conta de telefone fixo ou celular"
    },

    # Alimentação
    {
        "name": "Supermercado",
        "icon": "🛒",
        "color": "#16a085",
        "description": "Compras de supermercado"
    },
    {
        "name": "Feira",
        "icon": "🥬",
        "color": "#27ae60",
        "description": "Feira livre, frutas e verduras"
    },
    {
        "name": "Padaria",
        "icon": "🍞",
        "color": "#d68910",
        "description": "Padaria e lanches"
    },
    {
        "name": "Restaurante",
        "icon": "🍽️",
        "color": "#c0392b",
        "description": "Refeições em restaurantes"
    },
    {
        "name": "Delivery",
        "icon": "🛵",
        "color": "#d35400",
        "description": "Pedidos de comida por aplicativo"
    },

    # Transporte
    {
        "name": "Combustível",
        "icon": "⛽",
        "color": "#8e44ad",
        "description": "Gasolina, etanol, diesel"
    },
    {
        "name": "Transporte Público",
        "icon": "🚌",
        "color": "#2980b9",
        "description": "Ônibus, metrô, trem"
    },
    {
        "name": "Uber/Taxi",
        "icon": "🚕",
        "color": "#f1c40f",
        "description": "Corridas de aplicativo ou táxi"
    },
    {
        "name": "Estacionamento",
        "icon": "🅿️",
        "color": "#7f8c8d",
        "description": "Estacionamento"
    },
    {
        "name": "Manutenção Veículo",
        "icon": "🔧",
        "color": "#95a5a6",
        "description": "Manutenção e reparos do veículo"
    },
    {
        "name": "IPVA",
        "icon": "🚗",
        "color": "#c44569",
        "description": "Imposto sobre propriedade de veículo"
    },
    {
        "name": "Seguro Veículo",
        "icon": "🛡️",
        "color": "#546de5",
        "description": "Seguro do veículo"
    },

    # Saúde
    {
        "name": "Plano de Saúde",
        "icon": "🏥",
        "color": "#e55039",
        "description": "Mensalidade do plano de saúde"
    },
    {
        "name": "Farmácia",
        "icon": "💊",
        "color": "#4a69bd",
        "description": "Medicamentos e produtos de farmácia"
    },
    {
        "name": "Consultas Médicas",
        "icon": "👨‍⚕️",
        "color": "#0fbcf9",
        "description": "Consultas médicas particulares"
    },
    {
        "name": "Exames",
        "icon": "🔬",
        "color": "#4bcffa",
        "description": "Exames laboratoriais e diagnósticos"
    },
    {
        "name": "Dentista",
        "icon": "🦷",
        "color": "#05c46b",
        "description": "Tratamentos dentários"
    },

    # Educação
    {
        "name": "Escola",
        "icon": "🏫",
        "color": "#ffa502",
        "description": "Mensalidade escolar"
    },
    {
        "name": "Material Escolar",
        "icon": "📚",
        "color": "#ff6348",
        "description": "Livros, cadernos, materiais escolares"
    },
    {
        "name": "Cursos",
        "icon": "📖",
        "color": "#ff4757",
        "description": "Cursos extracurriculares"
    },
    {
        "name": "Faculdade",
        "icon": "🎓",
        "color": "#5f27cd",
        "description": "Mensalidade da faculdade"
    },

    # Lazer e Entretenimento
    {
        "name": "Streaming",
        "icon": "📺",
        "color": "#341f97",
        "description": "Netflix, Spotify, Amazon Prime, etc"
    },
    {
        "name": "Cinema",
        "icon": "🎬",
        "color": "#ee5a6f",
        "description": "Ingressos de cinema"
    },
    {
        "name": "Viagens",
        "icon": "✈️",
        "color": "#0abde3",
        "description": "Viagens e turismo"
    },
    {
        "name": "Lazer",
        "icon": "🎉",
        "color": "#10ac84",
        "description": "Atividades de lazer e diversão"
    },
    {
        "name": "Academia",
        "icon": "💪",
        "color": "#ee5a24",
        "description": "Mensalidade da academia"
    },
    {
        "name": "Esportes",
        "icon": "⚽",
        "color": "#00d2d3",
        "description": "Atividades esportivas"
    },

    # Vestuário
    {
        "name": "Roupas",
        "icon": "👕",
        "color": "#54a0ff",
        "description": "Compra de roupas"
    },
    {
        "name": "Calçados",
        "icon": "👟",
        "color": "#48dbfb",
        "description": "Compra de calçados"
    },
    {
        "name": "Acessórios",
        "icon": "👜",
        "color": "#ff9ff3",
        "description": "Bolsas, cintos, acessórios"
    },

    # Cuidados Pessoais
    {
        "name": "Salão/Barbearia",
        "icon": "💇",
        "color": "#feca57",
        "description": "Corte de cabelo, manicure, etc"
    },
    {
        "name": "Produtos de Higiene",
        "icon": "🧴",
        "color": "#ff6b6b",
        "description": "Shampoo, sabonete, produtos de higiene"
    },
    {
        "name": "Cosméticos",
        "icon": "💄",
        "color": "#f368e0",
        "description": "Maquiagem e cosméticos"
    },

    # Pets
    {
        "name": "Veterinário",
        "icon": "🐕",
        "color": "#1dd1a1",
        "description": "Consultas veterinárias"
    },
    {
        "name": "Pet Shop",
        "icon": "🐾",
        "color": "#76c893",
        "description": "Ração, produtos para pet"
    },

    # Serviços Domésticos
    {
        "name": "Empregada Doméstica",
        "icon": "🧹",
        "color": "#a29bfe",
        "description": "Serviços de limpeza"
    },
    {
        "name": "Lavanderia",
        "icon": "👔",
        "color": "#6c5ce7",
        "description": "Serviços de lavanderia"
    },

    # Outros
    {
        "name": "Seguros",
        "icon": "🛡️",
        "color": "#fd79a8",
        "description": "Seguros diversos"
    },
    {
        "name": "Doações",
        "icon": "🤝",
        "color": "#fdcb6e",
        "description": "Doações e caridade"
    },
    {
        "name": "Presentes",
        "icon": "🎁",
        "color": "#e17055",
        "description": "Compra de presentes"
    },
    {
        "name": "Impostos",
        "icon": "📋",
        "color": "#fab1a0",
        "description": "Impostos diversos"
    },
    {
        "name": "Cartão de Crédito",
        "icon": "💳",
        "color": "#74b9ff",
        "description": "Fatura do cartão de crédito"
    },
    {
        "name": "Empréstimos",
        "icon": "🏦",
        "color": "#a29bfe",
        "description": "Pagamento de empréstimos"
    },
    {
        "name": "Poupança",
        "icon": "💰",
        "color": "#55efc4",
        "description": "Depósito em poupança"
    },
    {
        "name": "Outros",
        "icon": "📦",
        "color": "#636e72",
        "description": "Outras despesas não categorizadas"
    },

    # Receitas
    {
        "name": "Salário",
        "icon": "💵",
        "color": "#00b894",
        "description": "Salário mensal"
    },
    {
        "name": "Freelance",
        "icon": "💼",
        "color": "#6c5ce7",
        "description": "Trabalhos freelance"
    },
    {
        "name": "Aluguel Recebido",
        "icon": "🏘️",
        "color": "#0984e3",
        "description": "Receita de aluguel"
    },
    {
        "name": "Rendimentos",
        "icon": "📊",
        "color": "#00cec9",
        "description": "Rendimentos de investimentos"
    },
    {
        "name": "Bônus",
        "icon": "🎯",
        "color": "#fdcb6e",
        "description": "Bônus e gratificações"
    },
    {
        "name": "Outras Receitas",
        "icon": "💸",
        "color": "#81ecec",
        "description": "Outras receitas diversas"
    },
]

# Métodos de pagamento padrão
DEFAULT_PAYMENT_METHODS = [
    {
        "name": "Não especificado",
        "description": "Método de pagamento não especificado",
        "icon": "❓",
        "is_default": True
    },
    {
        "name": "PIX",
        "description": "Pagamento via PIX",
        "icon": "📱"
    },
    {
        "name": "Dinheiro",
        "description": "Pagamento em dinheiro",
        "icon": "💵"
    },
    {
        "name": "Cartão de Débito",
        "description": "Pagamento com cartão de débito",
        "icon": "💳"
    },
    {
        "name": "Cartão de Crédito",
        "description": "Pagamento com cartão de crédito",
        "icon": "💎"
    },
    {
        "name": "Transferência Bancária",
        "description": "Transferência entre contas bancárias",
        "icon": "🏦"
    },
    {
        "name": "Boleto",
        "description": "Pagamento via boleto bancário",
        "icon": "🧾"
    },
    {
        "name": "Cheque",
        "description": "Pagamento com cheque",
        "icon": "📝"
    },
    {
        "name": "Vale Alimentação",
        "description": "Cartão ou vale alimentação",
        "icon": "🍽️"
    },
    {
        "name": "Vale Refeição",
        "description": "Cartão ou vale refeição",
        "icon": "🥗"
    }
]


def get_default_categories():
    """
    Retorna a lista de categorias padrão
    """
    return DEFAULT_CATEGORIES


def get_default_payment_methods():
    """
    Retorna a lista de métodos de pagamento padrão
    """
    return DEFAULT_PAYMENT_METHODS


def create_default_categories(user):
    """
    Cria as categorias padrão para um usuário

    Args:
        user: Usuário para associar as categorias

    Returns:
        int: Número de categorias criadas
    """
    from finance.models import Category

    created_count = 0

    for cat_data in DEFAULT_CATEGORIES:
        # Combinar o ícone com o nome para manter a informação visual
        category_name = f"{cat_data['icon']} {cat_data['name']}"

        category, created = Category.objects.get_or_create(
            user=user,
            name=category_name,
            defaults={
                'description': cat_data['description'],
                'color': cat_data['color']
            }
        )

        if created:
            created_count += 1

    return created_count


def create_default_payment_methods(user):
    """
    Cria os métodos de pagamento padrão para um usuário

    Args:
        user: Usuário para associar os métodos de pagamento

    Returns:
        int: Número de métodos de pagamento criados
    """
    from finance.models import PaymentMethod

    created_count = 0

    for method_data in DEFAULT_PAYMENT_METHODS:
        payment_method, created = PaymentMethod.objects.get_or_create(
            user=user,
            name=method_data['name'],
            defaults={
                'description': method_data['description'],
                'icon': method_data.get('icon', '💳'),
                'is_default': method_data.get('is_default', False),
                'is_active': True
            }
        )

        if created:
            created_count += 1

    return created_count