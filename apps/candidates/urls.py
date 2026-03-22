"""
URL patterns for candidate management.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_cv, name='candidate-upload'),
    path('', views.CandidateListView.as_view(), name='candidate-list'),
    path('<int:pk>/', views.CandidateDetailView.as_view(), name='candidate-detail'),
    path('<int:pk>/update/', views.CandidateUpdateView.as_view(), name='candidate-update'),
    path('<int:pk>/delete/', views.CandidateDeleteView.as_view(), name='candidate-delete'),
]