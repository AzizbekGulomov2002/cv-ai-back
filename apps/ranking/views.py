"""
Views for AI-powered candidate ranking system.
"""
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
import logging

from apps.audit.models import AuditLog
from apps.candidates.models import Candidate
from apps.jobs.models import Job
from services.ranking_service import RankingService
from .models import RankingSession, CandidateRanking
from .serializers import (
    RankingSessionSerializer, CandidateRankingSerializer,
    RankingRunSerializer, HumanOverrideSerializer,
    RankingAnalyticsSerializer
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
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
            ranking_service = RankingService()
            session = ranking_service.rank_candidates_for_job(
                job=job,
                candidates=candidates,
                user=request.user
            )
            
            # Update session notes if provided
            if notes:
                session.notes = notes
                session.save()
            
            # Log the ranking action
            AuditLog.log_ranking_action(
                user=request.user,
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
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
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
            
            # Apply human override
            ranking.set_human_override(
                decision=decision,
                user=request.user,
                score=score,
                feedback=feedback
            )
            
            # Log the override action
            AuditLog.log_human_override(
                user=request.user,
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
@permission_classes([IsAuthenticated])
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
    permission_classes = [IsAuthenticated]
    
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
    permission_classes = [IsAuthenticated]
    queryset = CandidateRanking.objects.all()