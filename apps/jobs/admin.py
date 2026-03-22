"""
Admin configuration for Job model.
"""
from django.contrib import admin
from .models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'level', 'job_type', 'min_experience', 'created_by', 'is_active', 'created_at']
    list_filter = ['job_type', 'level', 'is_active', 'created_by', 'created_at']
    search_fields = ['title', 'company', 'description', 'required_skills']
    readonly_fields = ['created_at', 'updated_at', 'embedding_vector']