from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
class User(AbstractUser):
    # Definindo os tipos de usuário
    class Role(models.TextChoices):
        FINANCE = 'finance', 'Financeiro'
        ATTENDANT = 'attendant', 'Atendente'
    """
    Modelo de usuário personalizado com campo de linguagem preferida
    """
    LANGUAGE_CHOICES = settings.LANGUAGES

    preferred_language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default=settings.LANGUAGE_CODE,
        verbose_name="Idioma Preferido",
        help_text="Idioma preferido do usuário para a interface"
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.FINANCE,
        verbose_name="Módulo do Usuário"
    )

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        return self.username or self.email
