"""
URL patterns for job management.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Shared (recruiter + candidate)
    path('', views.JobListView.as_view(), name='job-list'),
    path('for-upload/', views.job_choices_for_cv_upload, name='job-choices-cv-upload'),
    path('<int:pk>/', views.JobDetailView.as_view(), name='job-detail'),

    # Candidate-specific
    path('<int:pk>/apply-info/', views.job_apply_info, name='job-apply-info'),
    path('my-applications/', views.my_applications, name='my-applications'),

    # Recruiter-only
    path('create/', views.JobCreateView.as_view(), name='job-create'),
    path('<int:pk>/update/', views.JobUpdateView.as_view(), name='job-update'),
    path('<int:pk>/delete/', views.JobDeleteView.as_view(), name='job-delete'),
]