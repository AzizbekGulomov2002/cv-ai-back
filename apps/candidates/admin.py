"""
Admin configuration for Candidate model.
"""
from django.contrib import admin
from .models import Candidate


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'experience_years', 'uploaded_by', 'has_embedding', 'is_active', 'created_at']
    list_filter = ['is_active', 'experience_years', 'uploaded_by', 'created_at']
    search_fields = ['name', 'email', 'skills']
    readonly_fields = ['created_at', 'updated_at', 'extracted_text', 'embedding_vector']
    ordering = ['-created_at']