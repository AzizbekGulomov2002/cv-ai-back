"""
Serializers for candidate management.
"""
from rest_framework import serializers
from .models import Candidate


class CandidateUploadSerializer(serializers.ModelSerializer):
    """
    Serializer for candidate CV upload.
    """
    class Meta:
        model = Candidate
        fields = ['name', 'email', 'phone', 'cv_file']
    
    def validate_cv_file(self, value):
        """Validate CV file format."""
        if value:
            valid_extensions = ['.pdf', '.docx']
            file_extension = value.name.lower().split('.')[-1]
            if f'.{file_extension}' not in valid_extensions:
                raise serializers.ValidationError(
                    'Only PDF and DOCX files are supported.'
                )
            
            # Check file size (10MB limit)
            if value.size > 10 * 1024 * 1024:
                raise serializers.ValidationError(
                    'File size cannot exceed 10MB.'
                )
        
        return value


class CandidateSerializer(serializers.ModelSerializer):
    """
    Serializer for candidate information display.
    """
    file_extension = serializers.ReadOnlyField()
    has_embedding = serializers.ReadOnlyField()
    uploaded_by_username = serializers.CharField(
        source='uploaded_by.username', 
        read_only=True
    )
    
    class Meta:
        model = Candidate
        fields = [
            'id', 'name', 'email', 'phone', 'cv_file', 'file_extension',
            'skills', 'experience_years', 'education', 'has_embedding',
            'uploaded_by_username', 'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = [
            'id', 'extracted_text', 'embedding_vector', 
            'created_at', 'updated_at'
        ]


class CandidateDetailSerializer(CandidateSerializer):
    """
    Detailed serializer including extracted text (for authorized users).
    """
    class Meta(CandidateSerializer.Meta):
        fields = CandidateSerializer.Meta.fields + ['extracted_text']


class CandidateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating candidate information.
    """
    class Meta:
        model = Candidate
        fields = ['name', 'email', 'phone', 'skills', 'experience_years', 'education', 'is_active']