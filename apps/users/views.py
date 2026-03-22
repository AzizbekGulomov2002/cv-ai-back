"""
Views for user authentication and management.
"""
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.utils import timezone

from apps.audit.models import AuditLog
from .models import User
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer,
    UserProfileSerializer, UserUpdateSerializer
)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """
    User registration endpoint.
    """
    serializer = UserRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            user = serializer.save()
            
            # Create authentication token
            token, created = Token.objects.get_or_create(user=user)
            
            # Log registration action
            AuditLog.log_action(
                user=user,
                action_type='create',
                description=f"User {user.username} registered",
                content_object=user,
                risk_level='low',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            return Response({
                'message': 'User registered successfully',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role
                },
                'token': token.key
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # Log failed registration
            AuditLog.log_action(
                user=None,
                action_type='create',
                description=f"Failed user registration: {str(e)}",
                risk_level='medium',
                ip_address=request.META.get('REMOTE_ADDR'),
                success=False,
                error_message=str(e)
            )
            
            return Response({
                'error': 'Registration failed',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'error': 'Invalid registration data',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    User login endpoint.
    """
    serializer = UserLoginSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        try:
            # Create or get authentication token
            token, created = Token.objects.get_or_create(user=user)
            
            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            # Log login action
            AuditLog.log_action(
                user=user,
                action_type='login',
                description=f"User {user.username} logged in",
                content_object=user,
                risk_level='low',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'company': user.company
                },
                'token': token.key
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            # Log failed login
            AuditLog.log_action(
                user=user,
                action_type='login',
                description=f"Failed login for user {user.username}: {str(e)}",
                risk_level='medium',
                ip_address=request.META.get('REMOTE_ADDR'),
                success=False,
                error_message=str(e)
            )
            
            return Response({
                'error': 'Login failed',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'error': 'Invalid login credentials',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    User logout endpoint.
    """
    try:
        # Log logout action
        AuditLog.log_action(
            user=request.user,
            action_type='logout',
            description=f"User {request.user.username} logged out",
            content_object=request.user,
            risk_level='low',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Delete user's token
        try:
            Token.objects.get(user=request.user).delete()
        except Token.DoesNotExist:
            pass
        
        return Response({
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'Logout failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserProfileView(generics.RetrieveAPIView):
    """
    Get user profile information.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class UserUpdateView(generics.UpdateAPIView):
    """
    Update user profile information.
    """
    serializer_class = UserUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def perform_update(self, serializer):
        user = serializer.save()
        
        # Log profile update
        AuditLog.log_action(
            user=self.request.user,
            action_type='update',
            description=f"User {user.username} updated profile",
            content_object=user,
            risk_level='low',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )