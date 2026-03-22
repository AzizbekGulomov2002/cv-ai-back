"""
Admin configuration for Ranking models.
"""
from django.contrib import admin
from .models import RankingSession, CandidateRanking


@admin.register(RankingSession)
class RankingSessionAdmin(admin.ModelAdmin):
    list_display = ['job', 'created_by', 'candidates_count', 'use_openai_embeddings', 'created_at']
    list_filter = ['use_openai_embeddings', 'created_by', 'created_at']
    search_fields = ['job__title', 'notes']
    readonly_fields = ['created_at']


@admin.register(CandidateRanking)
class CandidateRankingAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'session', 'ai_rank', 'ai_score', 'human_decision', 'is_reviewed', 'has_bias_flags']
    list_filter = ['human_decision', 'reviewed_by', 'created_at', 'session__job']
    search_fields = ['candidate__name', 'explanation', 'human_feedback']
    readonly_fields = ['ai_score', 'ai_rank', 'matched_skills', 'missing_skills', 'explanation', 'bias_flags', 'created_at', 'updated_at']