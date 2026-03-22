"""
AI models for AI CV System.
"""
from django.db import models
from django.conf import settings


class AIConfiguration(models.Model):
    """
    Model to store AI system configurations.
    """
    name = models.CharField(max_length=100, unique=True, help_text='Configuration name')
    
    # OpenAI Configuration
    openai_model = models.CharField(
        max_length=50,
        default='text-embedding-3-small',
        help_text='OpenAI embedding model to use'
    )
    
    embedding_dimensions = models.PositiveIntegerField(
        default=1536,
        help_text='Embedding vector dimensions'
    )
    
    # Ranking Parameters
    similarity_threshold = models.FloatField(
        default=0.7,
        help_text='Minimum similarity threshold for matching'
    )
    
    # Bias Detection Settings
    bias_detection_enabled = models.BooleanField(
        default=True,
        help_text='Enable bias detection in rankings'
    )
    
    bias_keywords = models.JSONField(
        default=list,
        help_text='Keywords that might indicate bias'
    )
    
    # System Settings
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this configuration is active'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_configurations'
    )
    
    class Meta:
        db_table = 'ai_configurations'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"AI Config: {self.name}"
    
    @classmethod
    def get_active_config(cls):
        """Get the currently active AI configuration."""
        return cls.objects.filter(is_active=True).first()


class AIMetrics(models.Model):
    """
    Model to store AI system performance metrics.
    """
    METRIC_TYPES = [
        ('embedding_generation', 'Embedding Generation'),
        ('ranking_accuracy', 'Ranking Accuracy'),
        ('bias_detection', 'Bias Detection'),
        ('human_feedback', 'Human Feedback'),
    ]
    
    metric_type = models.CharField(
        max_length=30,
        choices=METRIC_TYPES,
        help_text='Type of metric being recorded'
    )
    
    metric_name = models.CharField(
        max_length=100,
        help_text='Specific metric name'
    )
    
    metric_value = models.FloatField(
        help_text='Numeric value of the metric'
    )
    
    metadata = models.JSONField(
        default=dict,
        help_text='Additional metadata about the metric'
    )
    
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    # Optional reference to related objects
    job_id = models.PositiveIntegerField(null=True, blank=True)
    candidate_id = models.PositiveIntegerField(null=True, blank=True)
    ranking_session_id = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'ai_metrics'
        ordering = ['-recorded_at']
        
    def __str__(self):
        return f"{self.metric_type}: {self.metric_name} = {self.metric_value}"


class EmbeddingCache(models.Model):
    """
    Model to cache embedding vectors to reduce API calls.
    """
    content_hash = models.CharField(
        max_length=64,
        unique=True,
        help_text='SHA-256 hash of the content'
    )
    
    content_type = models.CharField(
        max_length=20,
        choices=[
            ('cv_text', 'CV Text'),
            ('job_description', 'Job Description'),
        ],
        help_text='Type of content that was embedded'
    )
    
    embedding_vector = models.JSONField(
        help_text='The cached embedding vector'
    )
    
    model_used = models.CharField(
        max_length=50,
        help_text='OpenAI model used for embedding'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Usage tracking
    usage_count = models.PositiveIntegerField(
        default=1,
        help_text='Number of times this embedding has been reused'
    )
    
    last_used = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'embedding_cache'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Cached {self.content_type}: {self.content_hash[:8]}..."
    
    def increment_usage(self):
        """Increment usage counter when embedding is reused."""
        self.usage_count += 1
        self.save(update_fields=['usage_count', 'last_used'])