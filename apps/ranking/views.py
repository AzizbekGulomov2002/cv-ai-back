"""
Views for AI-powered candidate ranking system.
"""
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
import logging

from apps.audit.models import AuditLog
from apps.candidates.models import Candidate
from apps.jobs.models import Job
from apps.users.permissions import IsRecruiter
from services.api_actor import get_api_actor
from services.email_service import EmailService
from services.ranking_service import RankingService
from .models import RankingSession, CandidateRanking
from .rank_utils import leaderboard_rank_score_100
from .serializers import (
    RankingSessionSerializer, CandidateRankingSerializer,
    RankingRunSerializer, HumanOverrideSerializer,
    CandidateDecisionEmailSerializer,
)

logger = logging.getLogger(__name__)


@api_view(["POST"])
def preview_job_candidate_match(request):
    """
    Bitta job + nomzod uchun explainable match (ranking sessiyasini yaratmasdan).
    Dashboard / HR tekshiruvi.
    """
    job_id = request.data.get("job_id")
    candidate_id = request.data.get("candidate_id")
    if not job_id or not candidate_id:
        return Response(
            {"error": "job_id and candidate_id are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        job = get_object_or_404(Job, id=int(job_id), is_active=True)
        candidate = get_object_or_404(Candidate, id=int(candidate_id), is_active=True)
    except (TypeError, ValueError):
        return Response({"error": "Invalid id"}, status=status.HTTP_400_BAD_REQUEST)

    ranking_service = RankingService()
    _, errors = ranking_service.ensure_embeddings(
        Candidate.objects.filter(pk=candidate.pk), job
    )

    ev = ranking_service.evaluate_candidate_for_job(candidate, job)
    actor = get_api_actor(request)
    AuditLog.log_action(
        user=actor,
        action_type="read",
        description=f"Match preview job={job.id} candidate={candidate.id}",
        metadata={"job_id": job.id, "candidate_id": candidate.id},
        risk_level="low",
        ip_address=request.META.get("REMOTE_ADDR"),
    )

    return Response(
        {
            "message": "Match preview (decision-support only; not a hiring decision).",
            "job": {"id": job.id, "title": job.title},
            "candidate": {"id": candidate.id, "name": candidate.name},
            "embedding_warnings": errors,
            "match": {
                "composite_score": ev["score"],
                "match_breakdown": ev["match_breakdown"],
                "matched_skills": ev["matched_skills"],
                "missing_skills": ev["missing_skills"],
                "explanation": ev["explanation"],
                "bias_flags": ev["bias_flags"],
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
def run_ranking(request):
    """
    Run AI ranking for candidates against a job.
    """
    serializer = RankingRunSerializer(data=request.data)
    
    if serializer.is_valid():
        job_id = serializer.validated_data['job_id']
        candidate_ids = serializer.validated_data.get('candidate_ids')
        notes = serializer.validated_data.get('notes', '')
        only_target = serializer.validated_data.get('only_target_job_candidates', False)

        try:
            job = get_object_or_404(Job, id=job_id, is_active=True)

            # Get candidates to rank
            if candidate_ids:
                candidates = Candidate.objects.filter(
                    id__in=candidate_ids,
                    is_active=True
                )
            else:
                candidates = Candidate.objects.filter(is_active=True)
                if only_target:
                    candidates = candidates.filter(target_job_id=job_id)
            
            if not candidates.exists():
                return Response({
                    'error': 'No active candidates found'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Run the ranking process
            actor = get_api_actor(request)
            ranking_service = RankingService()
            session = ranking_service.rank_candidates_for_job(
                job=job,
                candidates=candidates,
                user=actor
            )
            
            # Update session notes if provided
            if notes:
                session.notes = notes
                session.save()
            
            # Log the ranking action
            AuditLog.log_ranking_action(
                user=actor,
                job=job,
                candidates_count=candidates.count(),
                ai_confidence=85.0,  # Mock confidence score
                metadata={
                    'session_id': session.id,
                    'candidates_ranked': candidates.count(),
                    'notes': notes
                },
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # Get the rankings
            rankings = CandidateRanking.objects.filter(
                session=session
            ).order_by('ai_rank')
            
            return Response({
                'message': 'Ranking completed successfully',
                'session': RankingSessionSerializer(session).data,
                'rankings_count': rankings.count(),
                'top_candidates': CandidateRankingSerializer(
                    rankings[:10], many=True
                ).data
            }, status=status.HTTP_200_OK)
            
        except Job.DoesNotExist:
            return Response({
                'error': 'Job not found or inactive'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error running ranking: {str(e)}")
            return Response({
                'error': 'Ranking process failed',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'error': 'Invalid ranking parameters',
        'details': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_job_rankings(request, job_id):
    """
    Get rankings for a specific job.

    Query: ``session_id`` — aniq sessiya (yo‘q bo‘lsa oxirgi).
    ``min_score`` — minimal ``ai_score``.
    ``human_decision`` — masalan ``pending``, ``accepted``.
    ``ordering`` — ``rank`` (sukut, ai_rank o‘sish) yoki ``-score``.
    """
    try:
        job = get_object_or_404(Job, id=job_id)

        session_id = request.query_params.get("session_id")
        if session_id:
            try:
                sid = int(session_id)
            except ValueError:
                return Response(
                    {"error": "Invalid session_id"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            latest_session = RankingSession.objects.filter(
                id=sid, job=job
            ).first()
        else:
            latest_session = RankingSession.objects.filter(
                job=job
            ).order_by("-created_at").first()

        if not latest_session:
            return Response({
                'message': 'No rankings found for this job',
                'job_title': job.title
            }, status=status.HTTP_404_NOT_FOUND)

        rankings = CandidateRanking.objects.filter(session=latest_session)

        min_score = request.query_params.get("min_score")
        if min_score is not None and min_score != "":
            try:
                rankings = rankings.filter(ai_score__gte=float(min_score))
            except ValueError:
                pass

        hum = request.query_params.get("human_decision")
        if hum:
            rankings = rankings.filter(human_decision=hum)

        ordering = (request.query_params.get("ordering") or "rank").lower()
        if ordering in ("-score", "score_desc"):
            rankings = rankings.order_by("-ai_score", "ai_rank")
        else:
            rankings = rankings.order_by("ai_rank")

        return Response({
            'job': {
                'id': job.id,
                'title': job.title
            },
            'session': RankingSessionSerializer(latest_session).data,
            'filters_applied': {
                'session_id': latest_session.id,
                'min_score': min_score,
                'human_decision': hum or None,
                'ordering': ordering,
            },
            'rankings': CandidateRankingSerializer(rankings, many=True).data
        }, status=status.HTTP_200_OK)
        
    except Job.DoesNotExist:
        return Response({
            'error': 'Job not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error getting job rankings: {str(e)}")
        return Response({
            'error': 'Failed to get rankings',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def override_ranking(request, ranking_id):
    """
    Human override of AI ranking decision.
    """
    try:
        ranking = get_object_or_404(CandidateRanking, id=ranking_id)
        serializer = HumanOverrideSerializer(data=request.data)
        
        if serializer.is_valid():
            decision = serializer.validated_data['human_decision']
            score = serializer.validated_data.get('human_score')
            feedback = serializer.validated_data.get('human_feedback', '')
            actor = get_api_actor(request)
            
            # Apply human override
            ranking.set_human_override(
                decision=decision,
                user=actor,
                score=score,
                feedback=feedback
            )
            
            # Log the override action
            AuditLog.log_human_override(
                user=actor,
                ranking=ranking,
                decision=decision,
                metadata={
                    'ai_score': ranking.ai_score,
                    'human_score': score,
                    'feedback': feedback
                },
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return Response({
                'message': 'Human override applied successfully',
                'ranking': CandidateRankingSerializer(ranking).data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'error': 'Invalid override data',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except CandidateRanking.DoesNotExist:
        return Response({
            'error': 'Ranking not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error applying human override: {str(e)}")
        return Response({
            'error': 'Override failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_ranking_analytics(request):
    """
    Get ranking analytics and performance metrics.
    """
    try:
        # Get query parameters
        job_id = request.query_params.get('job_id')
        days = int(request.query_params.get('days', 30))
        
        job = None
        if job_id:
            job = get_object_or_404(Job, id=job_id)
        
        # Get analytics from ranking service
        ranking_service = RankingService()
        analytics = ranking_service.get_ranking_analytics(job=job, days=days)
        
        return Response(analytics, status=status.HTTP_200_OK)
        
    except ValueError:
        return Response({
            'error': 'Invalid days parameter'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Job.DoesNotExist:
        return Response({
            'error': 'Job not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error getting ranking analytics: {str(e)}")
        return Response({
            'error': 'Analytics failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsRecruiter])
def candidate_rank_history(request, candidate_id):
    """
    All ranking results for one candidate across every session (newest session first).
    Each row includes ``rank`` and ``session_total`` for that run.
    """
    get_object_or_404(Candidate, pk=candidate_id, is_active=True)
    rows = (
        CandidateRanking.objects.filter(candidate_id=candidate_id)
        .select_related("session", "session__job")
        .order_by("-session__created_at", "ai_rank")
    )
    sessions_out = []
    for cr in rows:
        job = cr.session.job
        mb = cr.match_breakdown if isinstance(cr.match_breakdown, dict) else {}
        total = int(cr.session.candidates_count or mb.get("session_total") or 0)
        sessions_out.append(
            {
                "ranking_id": cr.id,
                "session_id": cr.session_id,
                "session_created_at": cr.session.created_at.isoformat()
                if cr.session.created_at
                else None,
                "job_id": job.id,
                "job_title": job.title,
                "company": getattr(job, "company", "") or "",
                "ai_rank": cr.ai_rank,
                "rank_position": cr.ai_rank,
                "rank": (
                    float(cr.rank)
                    if cr.rank is not None
                    else leaderboard_rank_score_100(cr.ai_rank, total)
                    if total
                    else None
                ),
                "session_total": total,
                "ai_score": round(float(cr.ai_score), 2),
                "final_score": round(float(cr.final_score), 2),
                "human_decision": cr.human_decision,
            }
        )
    return Response(
        {
            "candidate_id": candidate_id,
            "count": len(sessions_out),
            "sessions": sessions_out,
        },
        status=status.HTTP_200_OK,
    )


class RankingSessionListView(generics.ListAPIView):
    """
    List all ranking sessions (recruiters only).
    """
    serializer_class = RankingSessionSerializer
    permission_classes = [IsAuthenticated, IsRecruiter]

    def get_queryset(self):
        queryset = RankingSession.objects.all()

        job_id = self.request.query_params.get('job_id')
        if job_id:
            queryset = queryset.filter(job_id=job_id)

        min_c = self.request.query_params.get("min_candidates")
        if min_c:
            try:
                queryset = queryset.filter(candidates_count__gte=int(min_c))
            except ValueError:
                pass

        ordering = self.request.query_params.get("ordering", "-created_at")
        if ordering in ("created_at", "-created_at"):
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-created_at")

        return queryset


class CandidateRankingDetailView(generics.RetrieveAPIView):
    """
    Get detailed ranking info including scoring_summary (recruiter only).
    """
    serializer_class = CandidateRankingSerializer
    queryset = CandidateRanking.objects.all()
    permission_classes = [IsAuthenticated, IsRecruiter]


# ---------------------------------------------------------------------------
# Accept / Reject email endpoints
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsRecruiter])
def send_accept_email(request, ranking_id):
    """
    Recruiter accepts a candidate — sends personalised acceptance email via SMTP.

    Body (optional):
      extra_message (str): additional note to include in the email
    """
    ranking = get_object_or_404(CandidateRanking, id=ranking_id)
    candidate = ranking.candidate
    job = ranking.session.job
    actor = get_api_actor(request)

    candidate_email = candidate.email
    if not candidate_email or "@no-email" in candidate_email:
        # Try user account email
        if candidate.user and candidate.user.email:
            candidate_email = candidate.user.email
        else:
            return Response(
                {"error": "Candidate has no valid email address. Cannot send acceptance email."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    extra_message = (request.data.get("extra_message") or "").strip()

    mb = ranking.match_breakdown if isinstance(ranking.match_breakdown, dict) else {}
    scoring_summary = mb.get("scoring_summary")
    company_name = getattr(job, "company", "") or "Our Company"
    recruiter_name = (
        f"{actor.first_name} {actor.last_name}".strip() or actor.username
    )

    email_service = EmailService()
    sent = email_service.send_accept_email(
        candidate_email=candidate_email,
        candidate_name=candidate.name or "Candidate",
        job_title=job.title,
        company_name=company_name,
        recruiter_name=recruiter_name,
        ai_score=ranking.ai_score,
        matched_skills=list(ranking.matched_skills or []),
        scoring_summary=scoring_summary,
        extra_message=extra_message,
    )

    if not sent:
        return Response(
            {"error": "Failed to send email. Check SMTP configuration in .env."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    # Update ranking
    ranking.human_decision = 'accepted'
    ranking.email_sent = True
    ranking.email_sent_at = timezone.now()
    ranking.email_type = 'accept'
    if not ranking.reviewed_by:
        ranking.reviewed_by = actor
        ranking.reviewed_at = timezone.now()
    ranking.save()

    AuditLog.log_human_override(
        user=actor,
        ranking=ranking,
        decision='accepted',
        metadata={
            "email_sent_to": candidate_email,
            "ai_score": ranking.ai_score,
            "extra_message": extra_message,
        },
        ip_address=request.META.get('REMOTE_ADDR'),
    )

    return Response(
        {
            "message": f"Acceptance email sent to {candidate_email}.",
            "candidate": candidate.name,
            "job": job.title,
            "email_sent_to": candidate_email,
            "ranking": CandidateRankingSerializer(ranking).data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsRecruiter])
def send_reject_email(request, ranking_id):
    """
    Recruiter rejects a candidate — sends detailed rejection email via SMTP.

    Body:
      rejection_reasons (list[dict]): specific reasons — each with:
        - dimension (str)
        - score (float)
        - reason (str)
        - missing (list[str], optional)
      extra_message (str, optional): additional note to include
    """
    ranking = get_object_or_404(CandidateRanking, id=ranking_id)
    candidate = ranking.candidate
    job = ranking.session.job
    actor = get_api_actor(request)

    candidate_email = candidate.email
    if not candidate_email or "@no-email" in candidate_email:
        if candidate.user and candidate.user.email:
            candidate_email = candidate.user.email
        else:
            return Response(
                {"error": "Candidate has no valid email address. Cannot send rejection email."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # Build rejection reasons from request or auto-generate from match_breakdown
    rejection_reasons = request.data.get("rejection_reasons") or []
    extra_message = (request.data.get("extra_message") or "").strip()

    mb = ranking.match_breakdown if isinstance(ranking.match_breakdown, dict) else {}
    scoring_summary = mb.get("scoring_summary")

    # If no reasons provided, auto-generate from weak/average dimensions
    if not rejection_reasons and scoring_summary:
        for item in (scoring_summary.get("weak") or []):
            rejection_reasons.append({
                "dimension": item.get("label", item.get("id", "Area")),
                "score": item.get("score", 0),
                "reason": item.get("reason", ""),
                "missing": item.get("missing", []),
            })
        for item in (scoring_summary.get("average") or []):
            rejection_reasons.append({
                "dimension": item.get("label", item.get("id", "Area")),
                "score": item.get("score", 0),
                "reason": item.get("reason", ""),
                "missing": item.get("missing", []),
            })

    if not rejection_reasons:
        # Fallback: use missing_skills and explanation
        rejection_reasons = [
            {
                "dimension": "Overall Match",
                "score": ranking.ai_score,
                "reason": (ranking.explanation or "Profile did not meet current requirements.")[:300],
                "missing": list(ranking.missing_skills or [])[:8],
            }
        ]

    company_name = getattr(job, "company", "") or "Our Company"
    recruiter_name = (
        f"{actor.first_name} {actor.last_name}".strip() or actor.username
    )

    email_service = EmailService()
    sent = email_service.send_reject_email(
        candidate_email=candidate_email,
        candidate_name=candidate.name or "Candidate",
        job_title=job.title,
        company_name=company_name,
        recruiter_name=recruiter_name,
        ai_score=ranking.ai_score,
        rejection_reasons=rejection_reasons,
        scoring_summary=scoring_summary,
        extra_message=extra_message,
    )

    if not sent:
        return Response(
            {"error": "Failed to send email. Check SMTP configuration in .env."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    # Update ranking
    ranking.human_decision = 'rejected'
    ranking.rejection_reasons = rejection_reasons
    ranking.email_sent = True
    ranking.email_sent_at = timezone.now()
    ranking.email_type = 'reject'
    if not ranking.reviewed_by:
        ranking.reviewed_by = actor
        ranking.reviewed_at = timezone.now()
    ranking.save()

    AuditLog.log_human_override(
        user=actor,
        ranking=ranking,
        decision='rejected',
        metadata={
            "email_sent_to": candidate_email,
            "ai_score": ranking.ai_score,
            "rejection_reasons_count": len(rejection_reasons),
        },
        ip_address=request.META.get('REMOTE_ADDR'),
    )

    return Response(
        {
            "message": f"Rejection email sent to {candidate_email}.",
            "candidate": candidate.name,
            "job": job.title,
            "email_sent_to": candidate_email,
            "rejection_reasons_sent": rejection_reasons,
            "ranking": CandidateRankingSerializer(ranking).data,
        },
        status=status.HTTP_200_OK,
    )