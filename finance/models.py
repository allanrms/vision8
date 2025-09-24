from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from decimal import Decimal
import uuid


class Category(models.Model):
    """Categorias para segmentação das movimentações"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Usuário', null=True)
    name = models.CharField('Nome', max_length=100)
    description = models.TextField('Descrição', blank=True)
    color = models.CharField('Cor', max_length=7, default='#3498db', help_text='Código hex da cor (ex: #3498db)')
    is_active = models.BooleanField('Ativo', default=True)
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['name']

    def __str__(self):
        return self.name


class Movement(models.Model):
    """Movimentações financeiras (receitas e despesas)"""

    MOVEMENT_TYPES = (
        ('income', 'Receita'),
        ('expense', 'Despesa'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Usuário', null=True)
    type = models.CharField('Tipo', max_length=10, choices=MOVEMENT_TYPES)
    amount = models.DecimalField('Valor', max_digits=15, decimal_places=2,
                               validators=[MinValueValidator(Decimal('0.01'))])
    description = models.CharField('Descrição', max_length=200)
    date = models.DateField('Data')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name='Categoria')
    created_at = models.DateTimeField('Criado em', auto_now_add=True)
    updated_at = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Movimentação'
        verbose_name_plural = 'Movimentações'
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'type']),
            models.Index(fields=['user', 'category']),
        ]

    def __str__(self):
        signal = '+' if self.type == 'income' else '-'
        return f"{signal}R$ {self.amount} - {self.description} ({self.date})"
