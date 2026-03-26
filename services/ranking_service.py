"""
Ranking service for matching candidates to jobs using embeddings and similarity scoring.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from django.db.models import QuerySet

from apps.candidates.models import Candidate
from apps.jobs.models import Job
from apps.ranking.models import RankingSession, CandidateRanking
from .embedding_service import EmbeddingService
from .explain_service import ExplanationService

logger = logging.getLogger(__name__)


class RankingService:
    """
    Service class for ranking candidates against job requirements.
    """
    
    def __init__(self):
        """Initialize the ranking service."""
        self.embedding_service = EmbeddingService()
        self.explanation_service = ExplanationService()
    
    def ensure_embeddings(self, candidates: QuerySet[Candidate], job: Job) -> Tuple[bool, List[str]]:
        """
        Ensure all candidates and the job have embeddings generated.
        
        Args:
            candidates: QuerySet of candidates to check
            job: Job to check
            
        Returns:
            tuple: (success, list_of_error_messages)
        """
        errors = []
        
        # Check job embedding
        if not job.has_embedding:
            try:
                job_text = f"{job.title}\n{job.description}\n{job.requirements}"
                embedding, used_openai = self.embedding_service.generate_job_embedding(job_text)
                job.embedding_vector = embedding
                job.save()
                logger.info(f"Generated embedding for job: {job.title}")
            except Exception as e:
                error_msg = f"Failed to generate embedding for job {job.title}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Check candidate embeddings
        for candidate in candidates:
            if not candidate.has_embedding:
                try:
                    if not candidate.extracted_text:
                        errors.append(f"No extracted text for candidate {candidate.name}")
                        continue
                    
                    embedding, used_openai = self.embedding_service.generate_cv_embedding(
                        candidate.extracted_text
                    )
                    candidate.embedding_vector = embedding
                    candidate.save()
                    logger.info(f"Generated embedding for candidate: {candidate.name}")
                except Exception as e:
                    error_msg = f"Failed to generate embedding for candidate {candidate.name}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
        
        return len(errors) == 0, errors
    
    def _semantic_score_0_100(self, candidate: Candidate, job: Job) -> float:
        """Embedding cosine → 0–100 (match_breakdown ning semantic o‘lchami)."""
        if not candidate.has_embedding or not job.has_embedding:
            logger.warning(
                "Missing embeddings for candidate %s or job %s — semantic dimension = 0",
                candidate.name,
                job.title,
            )
            return 0.0
        try:
            return float(
                self.embedding_service.calculate_similarity_score(
                    candidate.embedding_vector,
                    job.embedding_vector,
                )
            )
        except Exception as e:
            logger.error("Semantic score error for %s: %s", candidate.name, e)
            return 0.0

    def evaluate_candidate_for_job(self, candidate: Candidate, job: Job) -> Dict:
        """
        Explainable score: o‘lchamlar, WHY matn, bias bayroqlari (EU AI Act style).
        """
        sem = self._semantic_score_0_100(candidate, job)
        breakdown = self.explanation_service.compute_match_breakdown(candidate, job, sem)
        score = float(breakdown["composite_score"])

        bias_h = self.explanation_service._check_for_bias_indicators(candidate, job)
        fairness = getattr(candidate, "fairness_scan_json", None) or {}
        bias_flags = self.explanation_service.merge_bias_flags_for_ranking(
            bias_h, fairness if isinstance(fairness, dict) else {}
        )

        dim_req = next(
            (d for d in breakdown["dimensions"] if d["id"] == "required_skills"), {}
        )
        dim_pref = next(
            (d for d in breakdown["dimensions"] if d["id"] == "preferred_skills"), {}
        )
        matched_skills = list(dim_req.get("matched") or []) + list(
            dim_pref.get("matched") or []
        )
        missing_skills = list(dim_req.get("missing") or [])
        explanation = self.explanation_service.narrative_from_match_breakdown(breakdown)

        return {
            "score": score,
            "match_breakdown": breakdown,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "explanation": explanation,
            "bias_flags": bias_flags,
        }

    def calculate_candidate_score(self, candidate: Candidate, job: Job) -> float:
        """Yagona raqam (faqat composite) — ranking ichida ``evaluate_candidate_for_job`` afzal."""
        return float(self.evaluate_candidate_for_job(candidate, job)["score"])
    
    def rank_candidates_for_job(self, job: Job, candidates: Optional[QuerySet[Candidate]] = None, 
                               user=None) -> RankingSession:
        """
        Rank all active candidates for a specific job.
        
        Args:
            job: Job to rank candidates for
            candidates: Optional specific candidates to rank (defaults to all active)
            user: User performing the ranking
            
        Returns:
            RankingSession: Created ranking session with results
        """
        if candidates is None:
            candidates = Candidate.objects.filter(is_active=True)
        
        # Ensure all candidates and job have embeddings
        success, errors = self.ensure_embeddings(candidates, job)
        if not success:
            logger.warning(f"Some embeddings failed to generate: {errors}")
        
        # Create ranking session
        session = RankingSession.objects.create(
            job=job,
            created_by=user,
            use_openai_embeddings=self.embedding_service.use_openai,
            candidates_count=candidates.count()
        )
        
        # Score all candidates (explainable dimensions)
        candidate_scores = []
        for candidate in candidates:
            ev = self.evaluate_candidate_for_job(candidate, job)
            candidate_scores.append((candidate, ev["score"], ev))
        
        # Sort by score (highest first)
        candidate_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Create ranking records (persist rank + session size inside match_breakdown for audit/UI)
        total_ranked = len(candidate_scores)
        ranking_objects = []
        for rank, (candidate, score, ev) in enumerate(candidate_scores, 1):
            rank_float = float(rank)
            mb = ev.get("match_breakdown")
            mb = dict(mb) if isinstance(mb, dict) else {}
            mb["rank"] = rank_float
            mb["session_total"] = total_ranked
            mb["session_id"] = session.id
            mb["job_id"] = job.id
            ss = mb.get("scoring_summary")
            if isinstance(ss, dict):
                ss = dict(ss)
                ss["rank"] = rank_float
                ss["session_total"] = total_ranked
                mb["scoring_summary"] = ss

            footer = self.explanation_service.leaderboard_footer_for_ranking(
                position=rank,
                session_total=total_ranked,
                rank_float=rank_float,
                composite_score=float(score),
                session_id=session.id,
                job_title=job.title,
            )
            explanation = (ev.get("explanation") or "") + footer

            ranking = CandidateRanking(
                session=session,
                candidate=candidate,
                ai_score=score,
                ai_rank=rank,
                rank=rank_float,
                matched_skills=ev["matched_skills"],
                missing_skills=ev["missing_skills"],
                explanation=explanation,
                bias_flags=ev.get("bias_flags", []),
                match_breakdown=mb,
            )
            ranking_objects.append(ranking)
        
        # Bulk create rankings for efficiency
        CandidateRanking.objects.bulk_create(ranking_objects)
        
        logger.info(f"Ranked {len(candidate_scores)} candidates for job: {job.title}")
        return session
    
    def get_top_candidates(self, job: Job, limit: int = 10) -> List[CandidateRanking]:
        """
        Get top ranked candidates for a job from the most recent ranking session.
        
        Args:
            job: Job to get candidates for
            limit: Maximum number of candidates to return
            
        Returns:
            List[CandidateRanking]: Top ranked candidates
        """
        latest_session = RankingSession.objects.filter(job=job).order_by('-created_at').first()
        
        if not latest_session:
            return []
        
        return CandidateRanking.objects.filter(
            session=latest_session
        ).order_by('ai_rank')[:limit]
    
    def rerank_with_feedback(self, ranking: CandidateRanking, human_score: float, 
                           feedback: str, user) -> CandidateRanking:
        """
        Update ranking with human feedback and potentially trigger reranking.
        
        Args:
            ranking: Ranking to update
            human_score: Human-assigned score
            feedback: Human feedback text
            user: User providing feedback
            
        Returns:
            CandidateRanking: Updated ranking
        """
        from django.utils import timezone
        
        # Update ranking with human feedback
        ranking.human_score = human_score
        ranking.human_feedback = feedback
        ranking.reviewed_by = user
        ranking.reviewed_at = timezone.now()
        ranking.save()
        
        logger.info(f"Updated ranking for {ranking.candidate.name} with human feedback")
        
        # TODO: In future versions, could use this feedback to improve AI model
        # self._learn_from_feedback(ranking)
        
        return ranking
    
    def get_ranking_analytics(self, job: Job = None, days: int = 30) -> Dict:
        """
        Get analytics about ranking performance.
        
        Args:
            job: Optional specific job to analyze
            days: Number of days to look back
            
        Returns:
            dict: Analytics data
        """
        from django.utils import timezone
        from django.db.models import Avg, Count, Q
        from datetime import timedelta
        
        try:
            # Base queryset
            base_qs = CandidateRanking.objects.filter(
                session__created_at__gte=timezone.now() - timedelta(days=days)
            )
            
            if job:
                base_qs = base_qs.filter(session__job=job)
            
            # Basic statistics
            stats = base_qs.aggregate(
                total_rankings=Count('id'),
                avg_ai_score=Avg('ai_score'),
                avg_human_score=Avg('human_score'),
                reviewed_count=Count('id', filter=Q(reviewed_by__isnull=False))
            )
            
            # Score distribution
            score_ranges = [
                ('90-100', base_qs.filter(ai_score__gte=90).count()),
                ('80-89', base_qs.filter(ai_score__gte=80, ai_score__lt=90).count()),
                ('70-79', base_qs.filter(ai_score__gte=70, ai_score__lt=80).count()),
                ('60-69', base_qs.filter(ai_score__gte=60, ai_score__lt=70).count()),
                ('Below 60', base_qs.filter(ai_score__lt=60).count()),
            ]
            
            # Human override statistics
            human_decisions = base_qs.filter(
                reviewed_by__isnull=False
            ).values('human_decision').annotate(
                count=Count('id')
            )
            
            return {
                'period_days': days,
                'job_title': job.title if job else 'All Jobs',
                'total_rankings': stats['total_rankings'] or 0,
                'average_ai_score': round(stats['avg_ai_score'] or 0, 2),
                'average_human_score': round(stats['avg_human_score'] or 0, 2),
                'review_rate': (
                    round((stats['reviewed_count'] or 0) / (stats['total_rankings'] or 1) * 100, 1)
                ),
                'score_distribution': score_ranges,
                'human_decisions': list(human_decisions),
                'embedding_service_stats': self.embedding_service.get_embedding_stats()
            }
            
        except Exception as e:
            logger.error(f"Error generating ranking analytics: {str(e)}")
            return {
                'error': str(e),
                'period_days': days,
                'job_title': job.title if job else 'All Jobs'
            }
    
    def bulk_rank_jobs(self, jobs: List[Job], user) -> List[RankingSession]:
        """
        Rank candidates for multiple jobs efficiently.
        
        Args:
            jobs: List of jobs to process
            user: User performing the ranking
            
        Returns:
            List[RankingSession]: Created ranking sessions
        """
        sessions = []
        candidates = Candidate.objects.filter(is_active=True)
        
        for job in jobs:
            try:
                session = self.rank_candidates_for_job(job, candidates, user)
                sessions.append(session)
                logger.info(f"Completed ranking for job: {job.title}")
            except Exception as e:
                logger.error(f"Failed to rank job {job.title}: {str(e)}")
        
        return sessions