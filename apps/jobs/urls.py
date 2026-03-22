"""
URL patterns for job management.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.JobListView.as_view(), name='job-list'),
    path(
        "for-upload/",
        views.job_choices_for_cv_upload,
        name="job-choices-cv-upload",
    ),
    path('create/', views.JobCreateView.as_view(), name='job-create'),
    path('<int:pk>/', views.JobDetailView.as_view(), name='job-detail'),
    path('<int:pk>/update/', views.JobUpdateView.as_view(), name='job-update'),
    path('<int:pk>/delete/', views.JobDeleteView.as_view(), name='job-delete'),
]