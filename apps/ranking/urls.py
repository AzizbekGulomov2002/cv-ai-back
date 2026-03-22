"""
URL patterns for AI-powered ranking system.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('run/', views.run_ranking, name='ranking-run'),
    path('<int:job_id>/', views.get_job_rankings, name='job-rankings'),
    path('<int:ranking_id>/override/', views.override_ranking, name='ranking-override'),
    path('analytics/', views.get_ranking_analytics, name='ranking-analytics'),
    path('sessions/', views.RankingSessionListView.as_view(), name='ranking-sessions'),
    path('details/<int:pk>/', views.CandidateRankingDetailView.as_view(), name='ranking-detail'),
]