"""
Candidate models for AI CV System.
"""
import os
import uuid

from django.conf import settings
from django.db import models


def candidate_file_path(instance, filename):
    """
    Upload path for CV files.

    Django may evaluate ``upload_to`` before the row has a primary key; using ``None``
    produced paths like ``cvs/None/file.pdf``. Use a stable folder per upload instead.
    """
    safe_name = os.path.basename(filename)
    folder = instance.pk if getattr(instance, "pk", None) else uuid.uuid4().hex[:12]
    return f"cvs/{folder}/{safe_name}"


class Candidate(models.Model):
    """
    Model to store candidate information and CV data.
    """
    # Basic Information (filled by OpenAI extraction after upload; may be blank until then)
    name = models.CharField(max_length=200, blank=True, default='', help_text='Full name')
    email = models.EmailField(blank=True, default='', help_text='Email address')
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

    # To‘liq strukturalangan chiqish (OpenAI / Gemini JSON) — audit va UI
    ai_profile_json = models.JSONField(
        default=dict,
        blank=True,
        help_text='Structured CV profile from LLM (OpenAI/Gemini) file extraction',
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
        if self.name or self.email:
            return f"{self.name or '—'} — {self.email or '—'}"
        return f"Candidate #{self.pk}"
    
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