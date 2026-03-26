"""
Views for user authentication and management.
"""
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.utils import timezone

from apps.audit.models import AuditLog
from .models import User
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserUpdateSerializer,
)


def _user_response(user, request):
    """Build a standardised user dict for login/register responses."""
    return UserProfileSerializer(user, context={'request': request}).data


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def register_view(request):
    """
    Register a new user (recruiter or candidate).
    Supports multipart/form-data for profile image upload.

    Required fields: username, email, password, password_confirm, role
    Candidate extras: first_name, last_name, github, image (file)
    Recruiter extras: company, phone
    """
    serializer = UserRegistrationSerializer(
        data=request.data,
        context={'request': request},
    )

    if serializer.is_valid():
        try:
            user = serializer.save()

            token, _ = Token.objects.get_or_create(user=user)

            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])

            AuditLog.log_action(
                user=user,
                action_type='create',
                description=f"User '{user.username}' registered as {user.role}",
                content_object=user,
                risk_level='low',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )

            return Response(
                {
                    'message': 'User registered successfully',
                    'token': token.key,
                    'user': _user_response(user, request),
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            AuditLog.log_action(
                user=None,
                action_type='create',
                description=f"Failed registration: {e}",
                risk_level='medium',
                ip_address=request.META.get('REMOTE_ADDR'),
                success=False,
                error_message=str(e),
            )
            return Response(
                {'error': 'Registration failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    return Response(
        {'error': 'Invalid registration data', 'details': serializer.errors},
        status=status.HTTP_400_BAD_REQUEST,
    )


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Login with username + password.
    Returns token + full user profile (including image_url, github,
    first_name, last_name, candidate_profile if role=candidate).
    """
    serializer = UserLoginSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.validated_data['user']

        try:
            token, _ = Token.objects.get_or_create(user=user)

            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])

            AuditLog.log_action(
                user=user,
                action_type='login',
                description=f"User '{user.username}' logged in",
                content_object=user,
                risk_level='low',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )

            return Response(
                {
                    'message': 'Login successful',
                    'token': token.key,
                    'user': _user_response(user, request),
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            AuditLog.log_action(
                user=user,
                action_type='login',
                description=f"Login error for '{user.username}': {e}",
                risk_level='medium',
                ip_address=request.META.get('REMOTE_ADDR'),
                success=False,
                error_message=str(e),
            )
            return Response(
                {'error': 'Login failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    return Response(
        {'error': 'Invalid login credentials', 'details': serializer.errors},
        status=status.HTTP_400_BAD_REQUEST,
    )


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout — invalidates the auth token."""
    try:
        AuditLog.log_action(
            user=request.user,
            action_type='logout',
            description=f"User '{request.user.username}' logged out",
            content_object=request.user,
            risk_level='low',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        Token.objects.filter(user=request.user).delete()
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': 'Logout failed', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ---------------------------------------------------------------------------
# Current user — /api/auth/me/
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """
    Returns the full profile of the currently logged-in user.

    For candidate accounts includes:
      candidate_profile: { id, name, email, phone, github, skills,
                           experience_years, education, cv_file_url,
                           target_job_id, ... }

    Use this on page load to restore session state.
    """
    return Response(
        _user_response(request.user, request),
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Profile detail / update
# ---------------------------------------------------------------------------

class UserProfileView(generics.RetrieveAPIView):
    """GET /api/auth/profile/ — same as /me/ but via class-based view."""
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx


class UserUpdateView(generics.UpdateAPIView):
    """
    PATCH /api/auth/profile/update/
    Update own profile. Supports multipart/form-data for image upload.
    Use PATCH (partial update) — all fields are optional.
    """
    serializer_class = UserUpdateSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ['patch', 'put', 'options', 'head']

    def get_object(self):
        return self.request.user

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx

    def perform_update(self, serializer):
        user = serializer.save()
        AuditLog.log_action(
            user=self.request.user,
            action_type='update',
            description=f"User '{user.username}' updated profile",
            content_object=user,
            risk_level='low',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
        )

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True   # always allow partial
        response = super().update(request, *args, **kwargs)
        # Re-read with full profile serializer so response includes image_url + candidate_profile
        response.data = _user_response(request.user, request)
        return response


# ---------------------------------------------------------------------------
# Image-only upload endpoint
# ---------------------------------------------------------------------------

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_profile_image(request):
    """
    PATCH /api/auth/profile/image/
    Upload or replace the profile photo only.
    Form field: image (file)
    Returns updated full user profile.
    """
    image = request.FILES.get('image')
    if not image:
        return Response(
            {'error': "No image file provided. Use form field 'image'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = request.user
    user.image = image
    user.save(update_fields=['image', 'updated_at'])

    AuditLog.log_action(
        user=user,
        action_type='update',
        description=f"User '{user.username}' uploaded profile image",
        content_object=user,
        risk_level='low',
        ip_address=request.META.get('REMOTE_ADDR'),
    )

    return Response(
        {
            'message': 'Profile image updated.',
            'user': _user_response(user, request),
        },
        status=status.HTTP_200_OK,
    )
