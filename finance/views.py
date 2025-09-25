from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from .models import Movement, Category, PaymentMethod
from authentication.decorators import finance_required
import json
import calendar


@finance_required
def dashboard(request):

    # Obter data atual
    today = timezone.now().date()

    # Definir período padrão como mês atual
    default_start = today.replace(day=1)
    default_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])

    # Obter datas do request ou usar padrão
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = default_start
            end_date = default_end
    else:
        start_date = default_start
        end_date = default_end

    movements = Movement.objects.filter(user=request.user, date__gte=start_date, date__lte=end_date)

    total_income = movements.filter(type='income').aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_expenses = movements.filter(type='expense').aggregate(total=Sum('amount'))['total'] or Decimal('0')
    balance = total_income - total_expenses

    expenses_by_cat = movements.filter(type='expense').values(
        'category__name', 'category__color'
    ).annotate(total=Sum('amount')).order_by('-total')

    expenses_by_category = []
    for exp in expenses_by_cat:
        percentage = (exp['total'] / total_expenses * 100) if total_expenses > 0 else 0
        expenses_by_category.append({
            'name': exp['category__name'],
            'color': exp['category__color'],
            'total': exp['total'],
            'percentage': percentage
        })

    # Receitas por categoria
    income_by_cat = movements.filter(type='income').values(
        'category__name', 'category__color'
    ).annotate(total=Sum('amount')).order_by('-total')

    income_by_category = []
    for inc in income_by_cat:
        percentage = (inc['total'] / total_income * 100) if total_income > 0 else 0
        income_by_category.append({
            'name': inc['category__name'],
            'color': inc['category__color'],
            'total': inc['total'],
            'percentage': percentage
        })

    # Agrupar dados diários (apenas dias com movimentação)
    daily_movements = movements.values('date', 'type').annotate(
        total=Sum('amount')
    ).order_by('date')

    # Criar dicionário para facilitar busca
    daily_dict = {}
    for mov in daily_movements:
        date_str = mov['date'].strftime('%d/%m')
        if date_str not in daily_dict:
            daily_dict[date_str] = {'income': 0, 'expenses': 0, 'date_obj': mov['date']}

        if mov['type'] == 'income':
            daily_dict[date_str]['income'] = float(mov['total'])
        elif mov['type'] == 'expense':
            daily_dict[date_str]['expenses'] = float(mov['total'])

    # GRÁFICO DE BARRAS: Mostrar apenas dias com movimentação
    bar_chart_data = []
    for date_str in sorted(daily_dict.keys(), key=lambda x: daily_dict[x]['date_obj']):
        data = daily_dict[date_str]
        bar_chart_data.append({
            'date': date_str,
            'income': data['income'],
            'expenses': data['expenses'],
            'balance': data['income'] - data['expenses']
        })

    # GRÁFICO DE LINHA: Mostrar evolução acumulada
    current_date = start_date
    balance_evolution = []
    accumulated_income = 0
    accumulated_expenses = 0
    accumulated_balance = 0

    while current_date <= end_date:
        date_str = current_date.strftime('%d/%m')
        has_movement = date_str in daily_dict

        if has_movement:
            income = daily_dict[date_str]['income']
            expenses = daily_dict[date_str]['expenses']
            accumulated_income += income
            accumulated_expenses += expenses
            accumulated_balance += (income - expenses)

        balance_evolution.append({
            'date': date_str,
            'income': accumulated_income,
            'expenses': accumulated_expenses,
            'balance': accumulated_balance,
            'has_movement': has_movement
        })

        current_date += timedelta(days=1)

    # Dados para gráfico de barras (apenas dias com movimentação)
    bar_labels = json.dumps([d['date'] for d in bar_chart_data])
    bar_income = json.dumps([d['income'] for d in bar_chart_data])
    bar_expenses = json.dumps([d['expenses'] for d in bar_chart_data])

    # Dados para gráfico de linha (evolução acumulada)
    evolution_labels = json.dumps([d['date'] for d in balance_evolution])
    evolution_income = json.dumps([d['income'] for d in balance_evolution])
    evolution_expenses = json.dumps([d['expenses'] for d in balance_evolution])
    evolution_balance = json.dumps([d['balance'] for d in balance_evolution])
    evolution_has_movement = json.dumps([d['has_movement'] for d in balance_evolution])

    expense_labels = json.dumps([cat['name'] for cat in expenses_by_category])
    expense_values = json.dumps([float(cat['total']) for cat in expenses_by_category])
    expense_colors = json.dumps([cat['color'] for cat in expenses_by_category])

    income_labels = json.dumps([cat['name'] for cat in income_by_category])
    income_values = json.dumps([float(cat['total']) for cat in income_by_category])
    income_colors = json.dumps([cat['color'] for cat in income_by_category])

    # Calcular número de dias do período
    period_days = (end_date - start_date).days + 1

    # Análise de despesas por método de pagamento
    expenses_by_payment_method = movements.filter(
        type='expense',
        payment_method__isnull=False
    ).values(
        'payment_method__name'
    ).annotate(total=Sum('amount')).order_by('-total')

    payment_methods_data = []
    for exp in expenses_by_payment_method:
        percentage = (exp['total'] / total_expenses * 100) if total_expenses > 0 else 0
        payment_methods_data.append({
            'name': exp['payment_method__name'],
            'total': exp['total'],
            'percentage': percentage
        })

    # Obter todas as movimentações do período ordenadas por data
    all_movements = movements.select_related('category', 'payment_method').order_by('-date', '-created_at')

    # Paginação
    page = request.GET.get('page', 1)
    paginator = Paginator(all_movements, 15)  # 15 transações por página
    paginated_movements = paginator.get_page(page)

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'period_days': period_days,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'balance': balance,
        'expenses_by_category': expenses_by_category,
        'income_by_category': income_by_category,
        'payment_methods_data': payment_methods_data,
        'all_movements': paginated_movements,
        'bar_labels': bar_labels,
        'bar_income': bar_income,
        'bar_expenses': bar_expenses,
        'evolution_labels': evolution_labels,
        'evolution_income': evolution_income,
        'evolution_expenses': evolution_expenses,
        'evolution_balance': evolution_balance,
        'evolution_has_movement': evolution_has_movement,
        'expense_labels': expense_labels,
        'expense_values': expense_values,
        'expense_colors': expense_colors,
        'income_labels': income_labels,
        'income_values': income_values,
        'income_colors': income_colors,
    }

    return render(request, 'finance/dashboard.html', context)


@finance_required
def categories_list(request):
    categories = Category.objects.filter(user=request.user).order_by('name')
    return render(request, 'finance/categories.html', {'categories': categories})


@finance_required
def category_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        color = request.POST.get('color', '#1e293b')
        Category.objects.create(user=request.user, name=name, color=color)
    return redirect('finance:categories')


@finance_required
def category_update(request, pk):
    if request.method == 'POST':
        category = get_object_or_404(Category, pk=pk, user=request.user)
        category.name = request.POST.get('name')
        category.color = request.POST.get('color', '#1e293b')
        category.save()
    return redirect('finance:categories')


@finance_required
def category_delete(request, pk):
    if request.method == 'POST':
        category = get_object_or_404(Category, pk=pk, user=request.user)
        category.delete()
    return redirect('finance:categories')
