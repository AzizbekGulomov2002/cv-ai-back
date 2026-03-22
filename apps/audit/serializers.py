"""
Serializers for audit logs and compliance reporting.
"""
from rest_framework import serializers
from .models import AuditLog, ComplianceReport


class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for audit log entries.
    """
    user_username = serializers.CharField(
        source='user.username',
        read_only=True
    )
    content_type_name = serializers.CharField(
        source='content_type.name',
        read_only=True
    )
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_username', 'action_type', 
            'action_description', 'content_type_name', 'object_id',
            'risk_level', 'metadata', 'ai_confidence', 'ai_explanation',
            'ip_address', 'timestamp', 'success', 'error_message'
        ]
        read_only_fields = ['id', 'timestamp']


class ComplianceReportSerializer(serializers.ModelSerializer):
    """
    Serializer for compliance reports.
    """
    generated_by_username = serializers.CharField(
        source='generated_by.username',
        read_only=True
    )
    
    class Meta:
        model = ComplianceReport
        fields = [
            'id', 'report_type', 'title', 'summary', 'period_start', 
            'period_end', 'generated_by_username', 'generated_at',
            'high_risk_actions_count', 'bias_incidents_count',
            'human_overrides_count'
        ]
        read_only_fields = ['id', 'generated_at']