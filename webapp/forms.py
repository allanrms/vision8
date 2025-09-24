"""
Formulários do Dashboard
Implementa validações e interface de usuário para gerenciamento de instâncias
"""

from django import forms


class LoginForm(forms.Form):
    """
    Formulário de login do sistema
    """
    username = forms.CharField(
        label='Usuário',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite seu usuário',
            'autocomplete': 'username'
        })
    )
    
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite sua senha',
            'autocomplete': 'current-password'
        })
    )


