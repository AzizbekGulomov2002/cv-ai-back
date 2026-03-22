"""
User models for AI CV System.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    """
    USER_ROLES = [
        ('recruiter', 'Recruiter'),
        ('hr_manager', 'HR Manager'),
        ('admin', 'Admin'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=USER_ROLES,
        default='recruiter',
        help_text='User role in the system'
    )
    
    company = models.CharField(
        max_length=200,
        blank=True,
        help_text='Company name'
    )
    
    phone = models.CharField(
        max_length=15,
        blank=True,
        help_text='Phone number'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
        
    def __str__(self):
        return f"{self.username} ({self.role})"