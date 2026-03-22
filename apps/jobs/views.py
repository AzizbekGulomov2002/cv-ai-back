"""
Views for job management.
"""
import logging

from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.audit.models import AuditLog
from services.api_actor import get_api_actor
from services.embedding_service import EmbeddingService
from .models import Job
from .serializers import JobCreateSerializer, JobMiniSerializer, JobSerializer, JobUpdateSerializer

logger = logging.getLogger(__name__)


@api_view(["GET"])
def job_choices_for_cv_upload(request):
    """
    CV yuklash formasi uchun: barcha aktiv vakansiyalar + UI matnlari (dinamik ro‘yxat).
    """
    jobs = Job.objects.filter(is_active=True).order_by("company", "title")
    ser = JobMiniSerializer(jobs, many=True)
    return Response(
        {
            "jobs": ser.data,
            "ui_prompt": {
                "uz": (
                    "Avval ariza berayotgan lavozimni tanlang. Bir nechta ochiq vakansiya bo‘lsa, "
                    "har biri uchun alohida CV yuklang yoki bir xil faylni turli job_id bilan yuboring. "
                    "Tanlangan vakansiya nomzod bilan bog‘lanadi va moslik (score) shu lavozim talablariga qarab hisoblanadi."
                ),
                "en": (
                    "Select the position this application is for. If you have several open roles, "
                    "upload once per job (same file is OK with different job_id). "
                    "The chosen job is stored on the candidate and the match score uses that job’s requirements."
                ),
            },
            "api": {
                "upload_multipart_fields": ["file|cv|cv_file", "job_id (optional but recommended)"],
                "upload_query": "?job_id=<id>",
                "example": "POST /api/candidates/upload/  Body: FormData file + job_id",
            },
        },
        status=status.HTTP_200_OK,
    )


class JobCreateView(generics.CreateAPIView):
    """
    Create a new job posting.
    """
    serializer_class = JobCreateSerializer
    
    def perform_create(self, serializer):
        actor = get_api_actor(self.request)
        job = serializer.save(created_by=actor)
        
        # Generate embedding for the job
        try:
            embedding_service = EmbeddingService()
            job_text = f"{job.title}\n{job.description}\n{job.requirements}"
            embedding, used_openai = embedding_service.generate_job_embedding(job_text)
            job.embedding_vector = embedding
            job.save()
            
            logger.info(f"Generated embedding for job {job.title} using {'OpenAI' if used_openai else 'dummy'}")
            
        except Exception as e:
            logger.warning(f"Failed to generate embedding for job {job.title}: {str(e)}")
        
        # Log the creation action
        AuditLog.log_action(
            user=actor,
            action_type='create',
            description=f"Created job posting: {job.title}",
            content_object=job,
            risk_level='medium',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )


class JobListView(generics.ListAPIView):
    """
    List all active job postings.
    """
    serializer_class = JobSerializer
    
    def get_queryset(self):
        queryset = Job.objects.filter(is_active=True)
        
        # Filter by search query
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                title__icontains=search
            ) | queryset.filter(
                company__icontains=search
            ) | queryset.filter(
                description__icontains=search
            )
        
        # Filter by job type
        job_type = self.request.query_params.get('job_type')
        if job_type:
            queryset = queryset.filter(job_type=job_type)
        
        # Filter by level
        level = self.request.query_params.get('level')
        if level:
            queryset = queryset.filter(level=level)
        
        # Filter by location
        location = self.request.query_params.get('location')
        if location:
            queryset = queryset.filter(location__icontains=location)
        
        return queryset.order_by('-created_at')


class JobDetailView(generics.RetrieveAPIView):
    """
    Get detailed job information.
    """
    serializer_class = JobSerializer
    queryset = Job.objects.all()


class JobUpdateView(generics.UpdateAPIView):
    """
    Update job information.
    """
    serializer_class = JobUpdateSerializer
    queryset = Job.objects.all()
    
    def perform_update(self, serializer):
        job = serializer.save()
        
        # Regenerate embedding if description or requirements changed
        if 'description' in serializer.validated_data or 'requirements' in serializer.validated_data:
            try:
                embedding_service = EmbeddingService()
                job_text = f"{job.title}\n{job.description}\n{job.requirements}"
                embedding, used_openai = embedding_service.generate_job_embedding(job_text)
                job.embedding_vector = embedding
                job.save()
                
                logger.info(f"Regenerated embedding for job {job.title}")
                
            except Exception as e:
                logger.warning(f"Failed to regenerate embedding for job {job.title}: {str(e)}")
        
        # Log the update action
        AuditLog.log_action(
            user=get_api_actor(self.request),
            action_type='update',
            description=f"Updated job posting: {job.title}",
            content_object=job,
            risk_level='low',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )


class JobDeleteView(generics.DestroyAPIView):
    """
    Delete (deactivate) a job posting.
    """
    queryset = Job.objects.all()
    
    def perform_destroy(self, instance):
        # Soft delete - just mark as inactive
        instance.is_active = False
        instance.save()
        
        # Log the deletion action
        AuditLog.log_action(
            user=get_api_actor(self.request),
            action_type='delete',
            description=f"Deactivated job posting: {instance.title}",
            content_object=instance,
            risk_level='medium',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )