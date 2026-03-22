"""
Audit models for AI CV System - MANDATORY for High-Risk AI System compliance.
"""
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import json


class AuditLog(models.Model):
    """
    Comprehensive audit log for all system actions.
    Required for high-risk AI system compliance (EU AI Act).
    """
    ACTION_TYPES = [
        ('create', 'Create'),
        ('read', 'Read'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('upload', 'Upload'),
        ('ranking', 'AI Ranking'),
        ('override', 'Human Override'),
        ('review', 'Human Review'),
        ('export', 'Data Export'),
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('ai_prediction', 'AI Prediction'),
        ('bias_check', 'Bias Check'),
    ]
    
    RISK_LEVELS = [
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk'),
    ]
    
    # Who performed the action
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs'
    )
    
    # What action was performed
    action_type = models.CharField(
        max_length=20,
        choices=ACTION_TYPES,
        help_text='Type of action performed'
    )
    
    action_description = models.CharField(
        max_length=500,
        help_text='Detailed description of the action'
    )
    
    # What object was affected (generic foreign key)
    content_type = models.ForeignKey(
        ContentType,
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )
    
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Risk assessment
    risk_level = models.CharField(
        max_length=10,
        choices=RISK_LEVELS,
        default='medium',
        help_text='Risk level of this action'
    )
    
    # Additional context data
    metadata = models.JSONField(
        default=dict,
        help_text='Additional context and data about the action'
    )
    
    # AI-specific fields
    ai_confidence = models.FloatField(
        null=True,
        blank=True,
        help_text='AI confidence score if applicable'
    )
    
    ai_explanation = models.TextField(
        blank=True,
        help_text='AI explanation or reasoning if applicable'
    )
    
    # Technical details
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address of the user'
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text='Browser/client user agent'
    )
    
    # Timestamps
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Success/failure tracking
    success = models.BooleanField(
        default=True,
        help_text='Whether the action was successful'
    )
    
    error_message = models.TextField(
        blank=True,
        help_text='Error message if action failed'
    )
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action_type', '-timestamp']),
            models.Index(fields=['risk_level', '-timestamp']),
            models.Index(fields=['content_type', 'object_id']),
        ]
        
    def __str__(self):
        return f"{self.timestamp}: {self.user} - {self.action_description}"
    
    @classmethod
    def log_action(cls, user, action_type, description, content_object=None, 
                   risk_level='medium', metadata=None, ai_confidence=None, 
                   ai_explanation='', ip_address=None, user_agent='', success=True, 
                   error_message=''):
        """
        Convenience method to create audit log entries.
        """
        return cls.objects.create(
            user=user,
            action_type=action_type,
            action_description=description,
            content_object=content_object,
            risk_level=risk_level,
            metadata=metadata or {},
            ai_confidence=ai_confidence,
            ai_explanation=ai_explanation,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message
        )
    
    @classmethod
    def log_ranking_action(cls, user, job, candidates_count, ai_confidence, 
                          metadata=None, ip_address=None):
        """
        Log AI ranking action with high-risk designation.
        """
        description = f"AI ranking performed for job '{job.title}' with {candidates_count} candidates"
        
        return cls.log_action(
            user=user,
            action_type='ranking',
            description=description,
            content_object=job,
            risk_level='high',
            metadata=metadata or {},
            ai_confidence=ai_confidence,
            ai_explanation="AI-generated candidate ranking based on CV-job matching",
            ip_address=ip_address
        )
    
    @classmethod
    def log_human_override(cls, user, ranking, decision, metadata=None, ip_address=None):
        """
        Log human override action.
        """
        description = f"Human override: {decision} for candidate {ranking.candidate.name}"
        
        return cls.log_action(
            user=user,
            action_type='override',
            description=description,
            content_object=ranking,
            risk_level='high',
            metadata=metadata or {},
            ip_address=ip_address
        )
    
    @classmethod
    def log_cv_upload(cls, user, candidate, metadata=None, ip_address=None):
        """
        Log CV upload action.
        """
        description = f"CV uploaded for candidate {candidate.name}"
        
        return cls.log_action(
            user=user,
            action_type='upload',
            description=description,
            content_object=candidate,
            risk_level='medium',
            metadata=metadata or {},
            ip_address=ip_address
        )


class ComplianceReport(models.Model):
    """
    Model to store compliance reports for regulatory requirements.
    """
    REPORT_TYPES = [
        ('daily', 'Daily Report'),
        ('weekly', 'Weekly Report'),
        ('monthly', 'Monthly Report'),
        ('audit', 'Audit Report'),
        ('incident', 'Incident Report'),
    ]
    
    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPES,
        help_text='Type of compliance report'
    )
    
    title = models.CharField(
        max_length=200,
        help_text='Report title'
    )
    
    report_data = models.JSONField(
        help_text='Structured report data'
    )
    
    summary = models.TextField(
        help_text='Executive summary of the report'
    )
    
    # Date range covered by report
    period_start = models.DateTimeField(
        help_text='Start date of the reporting period'
    )
    
    period_end = models.DateTimeField(
        help_text='End date of the reporting period'
    )
    
    # Report metadata
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='generated_compliance_reports'
    )
    
    generated_at = models.DateTimeField(auto_now_add=True)
    
    # Risk assessment
    high_risk_actions_count = models.PositiveIntegerField(
        default=0,
        help_text='Number of high-risk actions in this period'
    )
    
    bias_incidents_count = models.PositiveIntegerField(
        default=0,
        help_text='Number of potential bias incidents detected'
    )
    
    human_overrides_count = models.PositiveIntegerField(
        default=0,
        help_text='Number of human overrides performed'
    )
    
    class Meta:
        db_table = 'compliance_reports'
        ordering = ['-generated_at']
        
    def __str__(self):
        return f"{self.report_type.title()} Report: {self.title}"