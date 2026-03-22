"""
Admin configuration for User model.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin configuration for User model.
    """
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'company', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'date_joined', 'company']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'company']
    ordering = ['-date_joined']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'company', 'phone')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('email', 'first_name', 'last_name', 'role', 'company', 'phone')
        }),
    )