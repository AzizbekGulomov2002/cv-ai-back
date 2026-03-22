"""
Serializers for job management.
"""
from rest_framework import serializers
from .models import Job


class JobMiniSerializer(serializers.ModelSerializer):
    """CV upload / ro‘yxatlar uchun qisqa job kartochkasi."""

    class Meta:
        model = Job
        fields = ["id", "title", "company", "level", "location", "job_type"]


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
        read_only=True
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