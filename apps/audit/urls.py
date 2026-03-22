"""
URL patterns for audit logs and compliance.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.AuditLogListView.as_view(), name='audit-logs'),
    path('statistics/', views.audit_statistics, name='audit-statistics'),
]