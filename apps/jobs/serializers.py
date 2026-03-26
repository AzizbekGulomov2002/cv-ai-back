"""
Serializers for job management.
"""
from rest_framework import serializers
from .models import Job


class JobMiniSerializer(serializers.ModelSerializer):
    """CV upload / ro'yxatlar uchun qisqa job kartochkasi."""

    class Meta:
        model = Job
        fields = ["id", "title", "company", "level", "location", "job_type"]


class JobCandidateListSerializer(serializers.ModelSerializer):
    """
    Job list view for candidates — includes:
    - applicants_count: how many candidates applied
    - has_applied: whether this candidate has already applied
    - my_score: candidate's latest AI score for this job
    - my_status: candidate's human_decision status for this job
    """
    has_embedding = serializers.ReadOnlyField()
    salary_range = serializers.ReadOnlyField()
    all_skills = serializers.ReadOnlyField()
    applicants_count = serializers.SerializerMethodField()
    has_applied = serializers.SerializerMethodField()
    my_score = serializers.SerializerMethodField()
    my_status = serializers.SerializerMethodField()

    @staticmethod
    def get_applicants_count(obj):
        return getattr(obj, "_applicants_count", None)

    @staticmethod
    def get_has_applied(obj):
        return getattr(obj, "_has_applied", False)

    @staticmethod
    def get_my_score(obj):
        return getattr(obj, "_my_score", None)

    @staticmethod
    def get_my_status(obj):
        return getattr(obj, "_my_status", None)

    class Meta:
        model = Job
        fields = [
            "id", "title", "company", "location",
            "job_type", "level",
            "required_skills", "preferred_skills",
            "min_experience", "max_experience",
            "salary_min", "salary_max", "currency", "salary_range",
            "all_skills", "has_embedding",
            "application_deadline",
            "applicants_count",
            "has_applied", "my_score", "my_status",
            "created_at", "is_active",
        ]
        read_only_fields = ["id", "created_at"]


class JobCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating jobs.
    """
    class Meta:
        model = Job
        fields = [
            'title', 'company', 'location', 'description', 'requirements',
            'job_type', 'level', 'required_skills', 'preferred_skills',
            'min_experience', 'max_experience', 'salary_min', 'salary_max',
            'currency', 'application_deadline'
        ]


class JobSerializer(serializers.ModelSerializer):
    """
    Serializer for job information display.
    """
    has_embedding = serializers.ReadOnlyField()
    salary_range = serializers.ReadOnlyField()
    all_skills = serializers.ReadOnlyField()
    created_by_username = serializers.CharField(
        source='created_by.username',
        read_only=True,
    )

    class Meta:
        model = Job
        fields = [
            'id', 'title', 'company', 'location', 'description', 'requirements',
            'job_type', 'level', 'required_skills', 'preferred_skills',
            'min_experience', 'max_experience', 'salary_min', 'salary_max',
            'currency', 'salary_range', 'all_skills', 'has_embedding',
            'application_deadline', 'created_by_username', 'created_at',
            'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'embedding_vector', 'created_at', 'updated_at']


class JobUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating jobs.
    """
    class Meta:
        model = Job
        fields = [
            'title', 'company', 'location', 'description', 'requirements',
            'job_type', 'level', 'required_skills', 'preferred_skills',
            'min_experience', 'max_experience', 'salary_min', 'salary_max',
            'currency', 'application_deadline', 'is_active'
        ]
