"""
URL patterns for user authentication and management.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('register/', views.register_view, name='user-register'),
    path('login/', views.login_view, name='user-login'),
    path('logout/', views.logout_view, name='user-logout'),

    # Current user (session restore, rich profile)
    path('me/', views.me_view, name='user-me'),

    # Profile
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('profile/update/', views.UserUpdateView.as_view(), name='user-update'),
    path('profile/image/', views.upload_profile_image, name='user-image-upload'),
]
