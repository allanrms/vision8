"""
Views do WebApp
Dashboard principal e autenticação
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.response import Response
from rest_framework import status

from whatsapp_connector.models import EvolutionInstance, MessageHistory
from .forms import LoginForm


def login_view(request):
    """
    View de login do sistema
    """
    if request.user.is_authenticated:
        if hasattr(request.user, 'role'):
            if request.user.role == 'finance':
                return redirect('/finance/')
            elif request.user.role == 'attendant':
                return redirect('webapp:home')
        return redirect('webapp:home')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f'Bem-vindo, {user.get_full_name() or user.username}!')

                if hasattr(user, 'role'):
                    if user.role == 'finance':
                        return redirect('/finance/')
                    elif user.role == 'attendant':
                        return redirect('webapp:home')

                return redirect('webapp:home')
            else:
                messages.error(request, 'Credenciais inválidas. Tente novamente.')
    else:
        form = LoginForm()

    return render(request, 'webapp/login.html', {'form': form})


@login_required
def logout_view(request):
    """
    View de logout do sistema
    """
    logout(request)
    messages.info(request, 'Você foi desconectado com sucesso.')
    return redirect('webapp:login')


@login_required
def webapp_home(request):
    """
    Dashboard principal com estatísticas e resumo
    """
    # Estatísticas gerais filtradas por usuário
    total_instances = EvolutionInstance.objects.filter(owner=request.user).count()
    active_instances = EvolutionInstance.objects.filter(owner=request.user, is_active=True).count()
    connected_instances = EvolutionInstance.objects.filter(
        owner=request.user, status='connected', is_active=True
    ).count()
    
    # Mensagens das últimas 24h filtradas por usuário
    last_24h = timezone.now() - timedelta(hours=24)
    recent_messages = MessageHistory.objects.filter(
        received_at__gte=last_24h,
        owner=request.user
    ).count()
    
    # Instâncias por status filtradas por usuário
    status_counts = EvolutionInstance.objects.filter(owner=request.user).values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Últimas mensagens filtradas por usuário
    latest_messages = MessageHistory.objects.select_related(
        'chat_session'
    ).filter(
        owner=request.user
    ).order_by('-received_at')[:10]
    
    # Associar instâncias às mensagens (agora via relação direta)
    for message in latest_messages:
        if message.chat_session and message.chat_session.evolution_instance:
            message.evolution_instance = message.chat_session.evolution_instance
        else:
            message.evolution_instance = None
    
    # Instâncias recentes filtradas por usuário
    recent_instances = EvolutionInstance.objects.filter(owner=request.user).order_by('-created_at')[:5]
    
    context = {
        'total_instances': total_instances,
        'active_instances': active_instances,
        'connected_instances': connected_instances,
        'recent_messages_count': recent_messages,
        'status_counts': status_counts,
        'latest_messages': latest_messages,
        'recent_instances': recent_instances,
    }
    
    return render(request, 'webapp/home.html', context)


# API endpoints para gerenciamento de idioma
@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_available_languages(request):
    """
    Retorna os idiomas disponíveis no sistema
    """
    languages = [{'code': code, 'name': name} for code, name in settings.LANGUAGES]
    current_lang = getattr(request.user, 'preferred_language', settings.LANGUAGE_CODE)
    
    return Response({
        'languages': languages,
        'current': current_lang
    })


@api_view(['POST'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def set_user_language(request):
    """
    Define o idioma preferido do usuário
    """
    language_code = request.data.get('language')
    
    if not language_code:
        return Response({
            'error': str(_('Código do idioma é obrigatório'))
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Verificar se o idioma está disponível
    available_languages = [code for code, name in settings.LANGUAGES]
    if language_code not in available_languages:
        return Response({
            'error': str(_('Idioma "%(language)s" não disponível. Idiomas disponíveis: %(languages)s') % {
                'language': language_code,
                'languages': ', '.join(available_languages)
            })
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Atualizar preferência do usuário diretamente
    request.user.preferred_language = language_code
    request.user.save(update_fields=['preferred_language'])
    
    # Ativar idioma para esta sessão
    translation.activate(language_code)
    request.session['django_language'] = language_code
    
    return Response({
        'message': str(_('Idioma alterado para %(language)s') % {'language': language_code}),
        'language': language_code
    })


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_user_language(request):
    """
    Retorna o idioma preferido do usuário atual
    """
    user_language = getattr(request.user, 'preferred_language', settings.LANGUAGE_CODE)
    language_name = dict(settings.LANGUAGES).get(user_language, user_language)
    
    return Response({
        'language': user_language,
        'language_name': language_name
    })