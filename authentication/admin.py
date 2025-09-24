from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Admin personalizado para o modelo User
    """
    fieldsets = UserAdmin.fieldsets + (
        ('Preferências', {
            'fields': ('preferred_language', 'role')
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Preferências', {
            'fields': ('preferred_language', 'role')
        }),
    )

    list_display = UserAdmin.list_display + ('preferred_language', 'role')
    list_filter = UserAdmin.list_filter + ('preferred_language', 'role')
