from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from django.db import models
from .models import Category, Movement, PaymentMethod


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'color_display', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'user']
    search_fields = ['name', 'description', 'user__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
    list_editable = ['user',]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.user = request.user
        super().save_model(request, obj, form, change)

    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 5px 10px; border-radius: 3px; color: white;">{}</span>',
            obj.color, obj.color
        )
    color_display.short_description = 'Cor'


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'description', 'is_default', 'is_active', 'created_at']
    list_filter = ['is_default', 'is_active', 'created_at', 'user']
    search_fields = ['name', 'description', 'user__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
    list_editable = ['user', 'is_default', 'is_active']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Mostra métodos do usuário + métodos globais (user=None)
        return qs.filter(models.Q(user=request.user) | models.Q(user__isnull=True))

    def save_model(self, request, obj, form, change):
        if not change and not request.user.is_superuser:
            obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(Movement)
class MovementAdmin(admin.ModelAdmin):
    list_display = ['description', 'user', 'type_display', 'amount_display', 'category', 'payment_method', 'date']
    list_filter = ['type', 'category', 'payment_method', 'date', 'user']
    search_fields = ['description', 'user__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'date'
    list_editable = ['user', ]

    fieldsets = (
        ('Informações Básicas', {
            'fields': ('type', 'amount', 'description', 'date')
        }),
        ('Categorização', {
            'fields': ('category', 'payment_method')
        }),
        ('Metadados', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.user = request.user
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "category":
            if not request.user.is_superuser:
                kwargs["queryset"] = Category.objects.filter(user=request.user)
        elif db_field.name == "payment_method":
            if not request.user.is_superuser:
                kwargs["queryset"] = PaymentMethod.objects.filter(
                    models.Q(user=request.user) | models.Q(user__isnull=True),
                    is_active=True
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def type_display(self, obj):
        colors = {
            'income': 'green',
            'expense': 'red',
        }
        icons = {
            'income': '↗',
            'expense': '↙',
        }
        return format_html(
            '<span style="color: {};">{} {}</span>',
            colors.get(obj.type, 'black'),
            icons.get(obj.type, ''),
            obj.get_type_display()
        )
    type_display.short_description = 'Tipo'

    def amount_display(self, obj):
        color = 'green' if obj.type == 'income' else 'red'
        signal = '+' if obj.type == 'income' else '-'
        amount_formatted = f'{float(obj.amount):.2f}'
        return format_html(
            '<span style="color: {};">{} R$ {}</span>',
            color, signal, amount_formatted
        )
    amount_display.short_description = 'Valor'


# Customizar o admin site
admin.site.site_header = 'Orbi Finance - Administração'
admin.site.site_title = 'Orbi Finance'
admin.site.index_title = 'Gestão Financeira'
