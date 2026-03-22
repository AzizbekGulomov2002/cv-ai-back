"""
Serializers for AI-powered candidate ranking.
"""
from rest_framework import serializers
from .models import RankingSession, CandidateRanking
from apps.candidates.serializers import CandidateSerializer
from apps.jobs.serializers import JobSerializer


class RankingSessionSerializer(serializers.ModelSerializer):
    """
    Serializer for ranking sessions.
    """
    job_title = serializers.CharField(source='job.title', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = RankingSession
        fields = [
            'id', 'job', 'job_title', 'created_by_username', 'created_at',
            'use_openai_embeddings', 'candidates_count', 'notes'
        ]
        read_only_fields = ['id', 'created_at', 'use_openai_embeddings', 'candidates_count']


class CandidateRankingSerializer(serializers.ModelSerializer):
    """
    Serializer for individual candidate rankings.
    """
    candidate = CandidateSerializer(read_only=True)
    is_reviewed = serializers.ReadOnlyField()
    final_score = serializers.ReadOnlyField()
    has_bias_flags = serializers.ReadOnlyField()
    explanation_summary = serializers.ReadOnlyField()
    reviewed_by_username = serializers.CharField(
        source='reviewed_by.username', 
        read_only=True
    )
    
    class Meta:
        model = CandidateRanking
        fields = [
            'id', 'candidate', 'ai_score', 'ai_rank', 'matched_skills',
            'missing_skills', 'explanation', 'bias_flags', 'human_decision',
            'human_score', 'human_feedback', 'is_reviewed', 'final_score',
            'has_bias_flags', 'explanation_summary', 'reviewed_by_username',
            'reviewed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'ai_score', 'ai_rank', 'matched_skills', 'missing_skills',
            'explanation', 'bias_flags', 'created_at', 'updated_at',
            'reviewed_at'
        ]


class RankingRunSerializer(serializers.Serializer):
    """
    Serializer for initiating AI ranking process.
    """
    job_id = serializers.IntegerField()
    candidate_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="Optional list of candidate IDs to rank. If not provided, all active candidates will be ranked."
    )
    notes = serializers.CharField(
        max_length=1000, 
        required=False, 
        help_text="Optional notes about this ranking session"
    )


class HumanOverrideSerializer(serializers.Serializer):
    """
    Serializer for human override of AI rankings.
    """
    human_decision = serializers.ChoiceField(
        choices=CandidateRanking.DECISION_CHOICES
    )
    human_score = serializers.FloatField(
        min_value=0.0,
        max_value=100.0,
        required=False
    )
    human_feedback = serializers.CharField(
        max_length=1000,
        required=False
    )


class RankingAnalyticsSerializer(serializers.Serializer):
    """
    Serializer for ranking analytics data.
    """
    period_days = serializers.IntegerField(read_only=True)
    job_title = serializers.CharField(read_only=True)
    total_rankings = serializers.IntegerField(read_only=True)
    average_ai_score = serializers.FloatField(read_only=True)
    average_human_score = serializers.FloatField(read_only=True)
    review_rate = serializers.FloatField(read_only=True)
    score_distribution = serializers.ListField(read_only=True)
    human_decisions = serializers.ListField(read_only=True)
    embedding_service_stats = serializers.DictField(read_only=True)