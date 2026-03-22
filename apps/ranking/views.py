"""
Views for AI-powered candidate ranking system.
"""
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
import logging

from apps.audit.models import AuditLog
from apps.candidates.models import Candidate
from apps.jobs.models import Job
from services.api_actor import get_api_actor
from services.ranking_service import RankingService
from .models import RankingSession, CandidateRanking
from .serializers import (
    RankingSessionSerializer, CandidateRankingSerializer,
    RankingRunSerializer, HumanOverrideSerializer,
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
    """
    try:
        job = get_object_or_404(Job, id=job_id)
        
        # Get the latest ranking session for this job
        latest_session = RankingSession.objects.filter(
            job=job
        ).order_by('-created_at').first()
        
        if not latest_session:
            return Response({
                'message': 'No rankings found for this job',
                'job_title': job.title
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get all rankings for the latest session
        rankings = CandidateRanking.objects.filter(
            session=latest_session
        ).order_by('ai_rank')
        
        return Response({
            'job': {
                'id': job.id,
                'title': job.title
            },
            'session': RankingSessionSerializer(latest_session).data,
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


class RankingSessionListView(generics.ListAPIView):
    """
    List all ranking sessions.
    """
    serializer_class = RankingSessionSerializer
    
    def get_queryset(self):
        queryset = RankingSession.objects.all().order_by('-created_at')
        
        # Filter by job if provided
        job_id = self.request.query_params.get('job_id')
        if job_id:
            queryset = queryset.filter(job_id=job_id)
        
        return queryset


class CandidateRankingDetailView(generics.RetrieveAPIView):
    """
    Get detailed information about a specific ranking.
    """
    serializer_class = CandidateRankingSerializer
    queryset = CandidateRanking.objects.all()