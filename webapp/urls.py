"""
URLs do WebApp
Define rotas de autenticação e dashboard principal
"""

from django.urls import path
from . import views

app_name = 'webapp'

urlpatterns = [
    # Autenticação
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard principal
    path('', views.webapp_home, name='home'),
    path('home/', views.webapp_home, name='home_alt'),
    
    # API endpoints para idioma
    path('api/languages/', views.get_available_languages, name='api_available_languages'),
    path('api/language/', views.get_user_language, name='api_get_user_language'),
    path('api/language/set/', views.set_user_language, name='api_set_user_language'),
]