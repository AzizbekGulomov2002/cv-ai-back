"""
Ranking models for AI CV System.
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.ranking.rank_utils import leaderboard_rank_score_100


class RankingSession(models.Model):
    """
    Model to store ranking session information.
    """
    job = models.ForeignKey(
        'jobs.Job',
        on_delete=models.CASCADE,
        related_name='ranking_sessions'
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_ranking_sessions'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Ranking parameters
    use_openai_embeddings = models.BooleanField(
        default=True,
        help_text='Whether OpenAI embeddings were used'
    )
    
    candidates_count = models.PositiveIntegerField(
        default=0,
        help_text='Number of candidates ranked in this session'
    )
    
    # Session metadata
    notes = models.TextField(
        blank=True,
        help_text='Optional notes about the ranking session'
    )
    
    class Meta:
        db_table = 'ranking_sessions'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Ranking for {self.job.title} - {self.created_at.date()}"


class CandidateRanking(models.Model):
    """
    Model to store individual candidate rankings within a session.
    """
    DECISION_CHOICES = [
        ('pending', 'Pending Review'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('shortlisted', 'Shortlisted'),
    ]
    
    session = models.ForeignKey(
        RankingSession,
        on_delete=models.CASCADE,
        related_name='candidate_rankings'
    )
    
    candidate = models.ForeignKey(
        'candidates.Candidate',
        on_delete=models.CASCADE,
        related_name='rankings'
    )
    
    # AI-generated ranking
    ai_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text='AI-generated matching score (0-100)'
    )
    
    ai_rank = models.PositiveIntegerField(
        help_text='AI-generated rank position'
    )

    # 0–100 leaderboard rank score from position: 100*(N-pos+1)/N (1st of N → 100)
    rank = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text='Leaderboard rank on 0–100 scale from session position (best ≈ 100).',
    )

    # Explanation data (MANDATORY for high-risk AI system)
    matched_skills = models.JSONField(
        default=list,
        help_text='Skills that matched between candidate and job'
    )
    
    missing_skills = models.JSONField(
        default=list,
        help_text='Skills required by job but missing in candidate'
    )
    
    explanation = models.TextField(
        help_text='Human-readable explanation of the ranking decision'
    )
    
    # Bias detection results
    bias_flags = models.JSONField(
        default=list,
        help_text='Potential bias indicators detected'
    )

    # Per-dimension scores + WHY (semantic, skills, experience, …) — EU AI Act explainability
    match_breakdown = models.JSONField(
        default=dict,
        blank=True,
        help_text='Structured job–candidate match dimensions and narratives',
    )
    
    # Human override (MANDATORY for high-risk AI system)
    human_decision = models.CharField(
        max_length=20,
        choices=DECISION_CHOICES,
        default='pending',
        help_text='Human recruiter decision'
    )
    
    human_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text='Human-assigned score (0-100)'
    )
    
    human_feedback = models.TextField(
        blank=True,
        help_text='Human feedback on the AI recommendation'
    )
    
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_rankings'
    )
    
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When human review was conducted'
    )
    
    # Email notification tracking
    email_sent = models.BooleanField(
        default=False,
        help_text='Whether a decision email has been sent to the candidate',
    )
    email_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the decision email was sent',
    )
    email_type = models.CharField(
        max_length=20,
        blank=True,
        help_text='Type of last email sent: accept | reject',
    )

    # Structured rejection reasons (for reject emails and audit)
    rejection_reasons = models.JSONField(
        default=list,
        blank=True,
        help_text='List of specific rejection reasons with scores and explanations',
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'candidate_rankings'
        ordering = ['ai_rank']
        unique_together = ['session', 'candidate']
        
    def __str__(self):
        r = self.rank if self.rank is not None else float(self.ai_rank)
        return f"Rank #{self.ai_rank} (rank={r}): {self.candidate.name} (Score: {self.ai_score})"

    def save(self, *args, **kwargs):
        """Recompute ``rank`` (0–100) from ``ai_rank`` and session size."""
        if self.ai_rank is not None and self.session_id:
            total = 0
            if getattr(self, "session", None) is not None:
                total = int(self.session.candidates_count or 0)
            else:
                total = (
                    RankingSession.objects.filter(pk=self.session_id)
                    .values_list("candidates_count", flat=True)
                    .first()
                    or 0
                )
            if total <= 0:
                total = max(int(self.ai_rank), 1)
            self.rank = leaderboard_rank_score_100(self.ai_rank, total)
        super().save(*args, **kwargs)

    @property
    def session_total(self):
        """Number of candidates ranked in this session."""
        return int(self.session.candidates_count or 0)

    @property
    def is_reviewed(self):
        """Check if human review has been completed."""
        return self.reviewed_by is not None and self.reviewed_at is not None
    
    @property
    def final_score(self):
        """Get final score (human score if available, otherwise AI score)."""
        return self.human_score if self.human_score is not None else self.ai_score
    
    @property
    def has_bias_flags(self):
        """Check if any bias flags were detected."""
        return bool(self.bias_flags)
    
    def set_human_override(self, decision, user, score=None, feedback=""):
        """Set human override decision."""
        from django.utils import timezone
        
        self.human_decision = decision
        self.human_score = score
        self.human_feedback = feedback
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.save()
    
    @property
    def explanation_summary(self):
        """Get a summary of the ranking explanation."""
        return {
            'ai_score': self.ai_score,
            'matched_skills': self.matched_skills,
            'missing_skills': self.missing_skills,
            'explanation': self.explanation,
            'bias_flags': self.bias_flags,
            'match_breakdown': self.match_breakdown,
            'human_decision': self.human_decision,
            'is_reviewed': self.is_reviewed
        }