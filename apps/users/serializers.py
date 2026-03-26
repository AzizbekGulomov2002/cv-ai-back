"""
Serializers for user authentication and management.
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _absolute_image_url(request, image_field):
    """Return absolute URL for an ImageField value, or None if empty."""
    if not image_field:
        return None
    try:
        url = image_field.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Register a new user (recruiter or candidate).
    Supports multipart/form-data for image upload.

    Required: username, email, password, password_confirm, role
    Candidate extras: first_name, last_name, github, image
    Recruiter extras: company, phone
    """
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        validators=[validate_password],
    )
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'role',
            'company', 'phone',
            'image', 'github',
        ]
        extra_kwargs = {
            'image': {'required': False},
            'github': {'required': False},
            'company': {'required': False},
            'phone': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

    def validate_role(self, value):
        allowed = [User.ROLE_RECRUITER, User.ROLE_CANDIDATE]
        if value not in allowed:
            raise serializers.ValidationError(
                f"Role must be one of: {', '.join(allowed)}"
            )
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(
                {"password_confirm": "Password confirmation doesn't match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        # Extract image separately to avoid pk=None path issue
        image = validated_data.pop('image', None)
        user = User.objects.create_user(**validated_data)
        if image:
            user.image = image
            user.save(update_fields=['image'])
        return user


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class UserLoginSerializer(serializers.Serializer):
    """Login with username + password."""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid login credentials.')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            attrs['user'] = user
            return attrs

        raise serializers.ValidationError('Must include username and password.')


# ---------------------------------------------------------------------------
# Profile (read)
# ---------------------------------------------------------------------------

class CandidateProfileMiniSerializer(serializers.Serializer):
    """
    Embedded mini-summary of the linked Candidate record.
    Shown inside user profile responses for candidate accounts.
    """
    id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField()
    github = serializers.URLField()
    skills = serializers.ListField(child=serializers.CharField())
    experience_years = serializers.IntegerField(allow_null=True)
    education = serializers.CharField()
    professional_summary = serializers.CharField()
    cv_file = serializers.FileField()
    is_active = serializers.BooleanField()
    target_job_id = serializers.IntegerField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Full user profile. Includes:
    - image_url: absolute URL to profile photo
    - candidate_profile: linked Candidate record (if role=candidate)
    """
    image_url = serializers.SerializerMethodField()
    candidate_profile = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        request = self.context.get('request')
        return _absolute_image_url(request, obj.image)

    def get_candidate_profile(self, obj):
        """Return linked Candidate record summary for candidate users."""
        if obj.role != User.ROLE_CANDIDATE:
            return None
        candidate = getattr(obj, 'candidate_profile', None)
        if not candidate:
            return None
        request = self.context.get('request')
        cv_url = None
        if candidate.cv_file:
            try:
                cv_url = (
                    request.build_absolute_uri(candidate.cv_file.url)
                    if request else candidate.cv_file.url
                )
            except Exception:
                pass
        return {
            'id': candidate.id,
            'name': candidate.name,
            'email': candidate.email,
            'phone': candidate.phone,
            'github': candidate.github or None,
            'skills': candidate.skills,
            'experience_years': candidate.experience_years,
            'education': candidate.education,
            'professional_summary': candidate.professional_summary,
            'cv_file_url': cv_url,
            'is_active': candidate.is_active,
            'target_job_id': candidate.target_job_id,
            'created_at': candidate.created_at.isoformat() if candidate.created_at else None,
            'updated_at': candidate.updated_at.isoformat() if candidate.updated_at else None,
        }

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email',
            'first_name', 'last_name',
            'role',
            'company', 'phone',
            'image', 'image_url',
            'github',
            'date_joined', 'last_login',
            'candidate_profile',
        ]
        read_only_fields = [
            'id', 'username', 'date_joined', 'last_login',
            'image_url', 'candidate_profile',
        ]


# ---------------------------------------------------------------------------
# Profile update
# ---------------------------------------------------------------------------

class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Update own profile. Supports multipart/form-data for image.
    All fields optional — use PATCH.
    """
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        request = self.context.get('request')
        return _absolute_image_url(request, obj.image)

    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name',
            'company', 'phone',
            'image', 'image_url',
            'github',
        ]
        read_only_fields = ['image_url']
