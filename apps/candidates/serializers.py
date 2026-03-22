"""
Serializers for candidate management.
"""
import uuid

from rest_framework import serializers
from .models import Candidate


class CandidateUploadSerializer(serializers.ModelSerializer):
    """
    Serializer for candidate CV upload.

    Accepts multipart/form-data. File may be sent as ``cv_file`` (preferred),
    ``file``, or ``cv`` (common in frontends). Name/email may be omitted and
    filled after parsing, or use aliases ``full_name`` / ``fullName``.
    """

    file = serializers.FileField(write_only=True, required=False)
    cv = serializers.FileField(write_only=True, required=False)
    full_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    fullName = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Candidate
        fields = [
            "name",
            "email",
            "phone",
            "cv_file",
            "file",
            "cv",
            "full_name",
            "fullName",
        ]
        extra_kwargs = {
            "cv_file": {"required": False},
            "name": {"required": False, "allow_blank": True},
            "email": {"required": False, "allow_blank": True},
            "phone": {"required": False, "allow_blank": True},
        }

    def validate_cv_file(self, value):
        """Validate CV file format."""
        if value:
            self._validate_file_extension_and_size(value)
        return value

    def validate_file(self, value):
        if value:
            self._validate_file_extension_and_size(value)
        return value

    def validate_cv(self, value):
        if value:
            self._validate_file_extension_and_size(value)
        return value

    @staticmethod
    def _validate_file_extension_and_size(value):
        valid_extensions = [".pdf", ".docx"]
        file_extension = value.name.lower().split(".")[-1]
        if f".{file_extension}" not in valid_extensions:
            raise serializers.ValidationError("Only PDF and DOCX files are supported.")
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size cannot exceed 10MB.")

    def validate(self, attrs):
        """Resolve file aliases and optional name/email."""
        cv_file = attrs.get("cv_file") or attrs.pop("file", None) or attrs.pop("cv", None)
        if cv_file is None:
            raise serializers.ValidationError(
                {"cv_file": ["No file was submitted. Send the file as form field cv_file, file, or cv."]}
            )
        attrs["cv_file"] = cv_file

        data = getattr(self, "initial_data", None) or {}
        if hasattr(data, "get"):
            name = (attrs.get("name") or "").strip()
            if not name:
                name = (
                    (data.get("full_name") or data.get("fullName") or data.get("candidate_name") or "")
                    .strip()
                )
            attrs["name"] = name if name else "Unknown candidate"

            email = (attrs.get("email") or "").strip()
            if not email:
                email = (data.get("contact_email") or data.get("contactEmail") or "").strip()
            if not email:
                attrs["email"] = f"pending-{uuid.uuid4().hex[:12]}@parsed.invalid"
            else:
                attrs["email"] = email
        else:
            attrs.setdefault("name", "Unknown candidate")
            if not (attrs.get("email") or "").strip():
                attrs["email"] = f"pending-{uuid.uuid4().hex[:12]}@parsed.invalid"

        # Do not pass write-only helper fields to Candidate.objects.create
        attrs.pop("file", None)
        attrs.pop("cv", None)
        attrs.pop("full_name", None)
        attrs.pop("fullName", None)

        return attrs


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
