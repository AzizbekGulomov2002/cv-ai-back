"""
Job models for AI CV System.
"""
from django.db import models
from django.conf import settings


class Job(models.Model):
    """
    Model to store job descriptions and requirements.
    """
    JOB_TYPES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
    ]
    
    JOB_LEVELS = [
        ('junior', 'Junior'),
        ('mid', 'Mid-level'),
        ('senior', 'Senior'),
        ('lead', 'Lead'),
        ('manager', 'Manager'),
    ]
    
    # Basic Information
    title = models.CharField(max_length=200, help_text='Job title')
    company = models.CharField(max_length=200, help_text='Company name')
    location = models.CharField(max_length=200, help_text='Job location')
    
    # Job Details
    description = models.TextField(help_text='Detailed job description')
    requirements = models.TextField(help_text='Job requirements and qualifications')
    
    job_type = models.CharField(
        max_length=20,
        choices=JOB_TYPES,
        default='full_time',
        help_text='Type of employment'
    )
    
    level = models.CharField(
        max_length=20,
        choices=JOB_LEVELS,
        default='mid',
        help_text='Job level/seniority'
    )
    
    # Skills and Requirements
    required_skills = models.JSONField(
        default=list,
        help_text='Required skills as JSON array'
    )
    
    preferred_skills = models.JSONField(
        default=list,
        help_text='Preferred skills as JSON array'
    )
    
    min_experience = models.PositiveIntegerField(
        default=0,
        help_text='Minimum years of experience required'
    )
    
    max_experience = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Maximum years of experience'
    )
    
    # Salary Information
    salary_min = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Minimum salary'
    )
    
    salary_max = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Maximum salary'
    )
    
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text='Salary currency'
    )
    
    # Embeddings
    embedding_vector = models.JSONField(
        default=list,
        help_text='OpenAI embedding vector for job description'
    )
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_jobs'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    is_active = models.BooleanField(
        default=True,
        help_text='Whether job posting is active'
    )
    
    # Application deadline
    application_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Application deadline'
    )
    
    class Meta:
        db_table = 'jobs'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.title} at {self.company}"
    
    @property
    def has_embedding(self):
        """Check if job has embedding vector."""
        return bool(self.embedding_vector)
    
    @property
    def all_skills(self):
        """Get all required and preferred skills combined."""
        return list(set(self.required_skills + self.preferred_skills))
    
    @property
    def salary_range(self):
        """Get formatted salary range."""
        if self.salary_min and self.salary_max:
            return f"{self.salary_min} - {self.salary_max} {self.currency}"
        elif self.salary_min:
            return f"From {self.salary_min} {self.currency}"
        elif self.salary_max:
            return f"Up to {self.salary_max} {self.currency}"
        return "Not specified"