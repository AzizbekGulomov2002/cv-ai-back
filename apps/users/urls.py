"""
URL patterns for user authentication and management.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='user-register'),
    path('login/', views.login_view, name='user-login'),
    path('logout/', views.logout_view, name='user-logout'),
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('profile/update/', views.UserUpdateView.as_view(), name='user-update'),
]