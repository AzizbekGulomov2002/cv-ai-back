"""
User models for AI CV System.
"""
import os
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


def user_image_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    folder = instance.pk if getattr(instance, "pk", None) else uuid.uuid4().hex[:12]
    return f"user_images/{folder}/profile{ext}"


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    Roles: recruiter (hiring side) | candidate (job seeker).
    """
    ROLE_RECRUITER = 'recruiter'
    ROLE_CANDIDATE = 'candidate'

    USER_ROLES = [
        (ROLE_RECRUITER, 'Recruiter'),
        (ROLE_CANDIDATE, 'Candidate'),
    ]

    role = models.CharField(
        max_length=20,
        choices=USER_ROLES,
        default=ROLE_RECRUITER,
        help_text='User role: recruiter or candidate',
    )

    company = models.CharField(
        max_length=200,
        blank=True,
        help_text='Company name (for recruiters)',
    )

    phone = models.CharField(
        max_length=15,
        blank=True,
        help_text='Phone number',
    )

    image = models.ImageField(
        upload_to=user_image_path,
        null=True,
        blank=True,
        help_text='Profile photo',
    )

    github = models.URLField(
        max_length=300,
        blank=True,
        help_text='GitHub profile URL (for candidates)',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def is_recruiter(self):
        return self.role == self.ROLE_RECRUITER

    @property
    def is_candidate(self):
        return self.role == self.ROLE_CANDIDATE