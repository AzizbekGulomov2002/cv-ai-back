"""
URL patterns for recruiter statistics dashboard.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.recruiter_dashboard, name='stats-dashboard'),
    path('jobs/<int:job_id>/', views.job_stats_detail, name='stats-job-detail'),
]
