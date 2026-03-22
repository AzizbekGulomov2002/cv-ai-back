"""
Candidate models for AI CV System.
"""
from django.db import models
from django.conf import settings
import os


def candidate_file_path(instance, filename):
    """Generate upload path for candidate CV files."""
    return f'cvs/{instance.id}/{filename}'


class Candidate(models.Model):
    """
    Model to store candidate information and CV data.
    """
    # Basic Information
    name = models.CharField(max_length=200, help_text='Full name')
    email = models.EmailField(help_text='Email address')
    phone = models.CharField(max_length=15, blank=True, help_text='Phone number')
    
    # CV File
    cv_file = models.FileField(
        upload_to=candidate_file_path,
        help_text='Uploaded CV file (PDF/DOCX)'
    )
    
    # Extracted Information
    extracted_text = models.TextField(
        blank=True,
        help_text='Text extracted from CV'
    )
    
    skills = models.JSONField(
        default=list,
        help_text='Extracted skills as JSON array'
    )
    
    experience_years = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Years of experience'
    )
    
    education = models.TextField(
        blank=True,
        help_text='Education information'
    )
    
    # Embeddings
    embedding_vector = models.JSONField(
        default=list,
        help_text='OpenAI embedding vector'
    )
    
    # Metadata
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='uploaded_candidates'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    is_active = models.BooleanField(
        default=True,
        help_text='Whether candidate profile is active'
    )
    
    class Meta:
        db_table = 'candidates'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.name} - {self.email}"
    
    @property
    def file_extension(self):
        """Get the file extension of the uploaded CV."""
        if self.cv_file:
            return os.path.splitext(self.cv_file.name)[1].lower()
        return None
    
    @property
    def has_embedding(self):
        """Check if candidate has embedding vector."""
        return bool(self.embedding_vector)
    
    def delete(self, *args, **kwargs):
        """Delete CV file when candidate is deleted."""
        if self.cv_file:
            try:
                os.remove(self.cv_file.path)
            except (OSError, ValueError):
                pass
        super().delete(*args, **kwargs)