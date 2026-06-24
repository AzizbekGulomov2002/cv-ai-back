"""
Views for job management.
"""
import logging

from django.db.models import Count, OuterRef, Subquery, FloatField
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from apps.users.permissions import IsRecruiter, OptionalAuth
from services.api_actor import get_api_actor
from services.embedding_service import EmbeddingService
from .models import Job
from .serializers import (
    JobCreateSerializer,
    JobMiniSerializer,
    JobSerializer,
    JobUpdateSerializer,
    JobCandidateListSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Candidate-facing: job browsing + application status
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([OptionalAuth])
def job_choices_for_cv_upload(request):
    """
    CV yuklash formasi uchun: barcha aktiv vakansiyalar + UI matnlari.
    Auth required.
    """
    jobs = Job.objects.filter(is_active=True).order_by("company", "title")
    ser = JobMiniSerializer(jobs, many=True)
    return Response(
        {
            "jobs": ser.data,
            "ui_prompt": {
                "uz": (
                    "Avval ariza berayotgan lavozimni tanlang. Bir nechta ochiq vakansiya bo'lsa, "
                    "har biri uchun alohida CV yuklang yoki bir xil faylni turli job_id bilan yuboring."
                ),
                "en": (
                    "Select the position this application is for. "
                    "The chosen job is stored on the candidate and the match score uses that job's requirements."
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


@api_view(["GET"])
@permission_classes([OptionalAuth])
def job_apply_info(request, pk):
    """
    Candidate-facing job detail with application status for the requesting user.

    Returns full job details plus:
    - has_applied: whether the candidate has already applied
    - my_candidate_id: their candidate record ID
    - my_score: their latest AI score for this job (if ranked)
    - my_rank: their rank in the latest session
    - my_status: human_decision (pending/accepted/rejected/shortlisted)
    - scoring_summary: their breakdown (strong/average/weak)
    - email_sent: whether an email was sent to them
    """
    from apps.candidates.models import Candidate
    from apps.ranking.models import CandidateRanking, RankingSession

    job = Job.objects.filter(pk=pk, is_active=True).first()
    if not job:
        return Response({"error": "Job not found or inactive."}, status=status.HTTP_404_NOT_FOUND)

    data = JobSerializer(job).data
    data["has_applied"] = False
    data["my_candidate_id"] = None
    data["my_score"] = None
    data["my_rank"] = None
    data["my_status"] = None
    data["my_email_sent"] = False
    data["my_email_type"] = None
    data["scoring_summary"] = None
    data["matched_skills"] = None
    data["missing_skills"] = None

    # Check if this user is a candidate with a profile
    user = request.user
    if getattr(user, "is_authenticated", False) and getattr(user, "role", None) == "candidate":
        candidate = Candidate.objects.filter(user=user, is_active=True).first()
        if candidate:
            # Check if applied for this job
            if candidate.target_job_id == job.id:
                data["has_applied"] = True
                data["my_candidate_id"] = candidate.id

                # Get latest ranking for this job
                session = (
                    RankingSession.objects.filter(job=job)
                    .order_by("-created_at")
                    .first()
                )
                if session:
                    cr = CandidateRanking.objects.filter(
                        session=session, candidate=candidate
                    ).first()
                    if cr:
                        data["my_score"] = cr.ai_score
                        data["my_rank"] = cr.ai_rank
                        data["my_status"] = cr.human_decision
                        data["my_email_sent"] = cr.email_sent
                        data["my_email_type"] = cr.email_type
                        data["matched_skills"] = cr.matched_skills
                        data["missing_skills"] = cr.missing_skills
                        mb = cr.match_breakdown if isinstance(cr.match_breakdown, dict) else {}
                        data["scoring_summary"] = mb.get("scoring_summary")
    elif getattr(user, "is_authenticated", False) and getattr(user, "role", None) == "recruiter":
        # Recruiters see total applicants for this job
        data["applicants_count"] = Candidate.objects.filter(
            target_job=job, is_active=True
        ).count()

    return Response(data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([OptionalAuth])
def my_applications(request):
    """
    Candidate: list all jobs they have applied to with their scores and status.
    Recruiter: returns 403.
    """
    from apps.candidates.models import Candidate
    from apps.ranking.models import CandidateRanking, RankingSession

    if not getattr(request.user, "is_authenticated", False):
        return Response(
            {
                "message": "Login to see your applications.",
                "has_profile": False,
                "applications": [],
            },
            status=status.HTTP_200_OK,
        )

    if getattr(request.user, "role", None) != "candidate":
        return Response(
            {"error": "This endpoint is for candidates only."},
            status=status.HTTP_403_FORBIDDEN,
        )

    candidate = Candidate.objects.filter(user=request.user, is_active=True).first()
    if not candidate:
        return Response(
            {
                "message": "You have not uploaded a CV yet.",
                "has_profile": False,
                "applications": [],
            },
            status=status.HTTP_200_OK,
        )

    # The candidate can only apply to one job (target_job), but show history
    applications = []
    if candidate.target_job_id:
        job = candidate.target_job
        app_entry = {
            "job_id": job.id,
            "job_title": job.title,
            "company": job.company,
            "location": job.location,
            "job_type": job.job_type,
            "level": job.level,
            "applied_at": candidate.created_at.isoformat(),
            "candidate_id": candidate.id,
            "score": None,
            "rank": None,
            "status": "applied",
            "email_sent": False,
            "email_type": None,
            "scoring_summary": None,
            "matched_skills": list(candidate.skills or []),
        }

        session = (
            RankingSession.objects.filter(job=job).order_by("-created_at").first()
        )
        if session:
            cr = CandidateRanking.objects.filter(
                session=session, candidate=candidate
            ).first()
            if cr:
                app_entry["score"] = cr.ai_score
                app_entry["rank"] = cr.ai_rank
                app_entry["status"] = cr.human_decision
                app_entry["email_sent"] = cr.email_sent
                app_entry["email_type"] = cr.email_type
                app_entry["matched_skills"] = cr.matched_skills
                app_entry["missing_skills"] = cr.missing_skills
                mb = cr.match_breakdown if isinstance(cr.match_breakdown, dict) else {}
                app_entry["scoring_summary"] = mb.get("scoring_summary")

        applications.append(app_entry)

    return Response(
        {
            "has_profile": True,
            "candidate_id": candidate.id,
            "candidate_name": candidate.name,
            "applications": applications,
        },
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Shared: Job list (annotated differently by role)
# ---------------------------------------------------------------------------

class JobListView(generics.ListAPIView):
    """
    List all active job postings. Auth required.

    - Candidate role: each job annotated with has_applied, my_score, my_status, applicants_count
    - Recruiter role: each job annotated with applicants_count

    Query params: search, job_type, level, location
    """
    permission_classes = [OptionalAuth]

    def get_serializer_class(self):
        return JobCandidateListSerializer

    def get_queryset(self):
        queryset = Job.objects.filter(is_active=True)

        search = self.request.query_params.get("search")
        if search:
            queryset = (
                queryset.filter(title__icontains=search)
                | queryset.filter(company__icontains=search)
                | queryset.filter(description__icontains=search)
            )

        job_type = self.request.query_params.get("job_type")
        if job_type:
            queryset = queryset.filter(job_type=job_type)

        level = self.request.query_params.get("level")
        if level:
            queryset = queryset.filter(level=level)

        location = self.request.query_params.get("location")
        if location:
            queryset = queryset.filter(location__icontains=location)

        return queryset.order_by("-created_at")

    def list(self, request, *args, **kwargs):
        from apps.candidates.models import Candidate
        from apps.ranking.models import CandidateRanking, RankingSession

        queryset = self.get_queryset()

        # Annotate applicants_count for all jobs
        from django.db.models import Count as DjCount
        applicants_map = {
            item["target_job_id"]: item["cnt"]
            for item in Candidate.objects.filter(is_active=True)
            .values("target_job_id")
            .annotate(cnt=DjCount("id"))
        }

        # For candidates: look up their own application status per job
        candidate = None
        if getattr(request.user, "is_authenticated", False) and getattr(request.user, "role", None) == "candidate":
            candidate = Candidate.objects.filter(
                user=request.user, is_active=True
            ).first()

        jobs_list = list(queryset)
        for job in jobs_list:
            job._applicants_count = applicants_map.get(job.id, 0)
            job._has_applied = False
            job._my_score = None
            job._my_status = None

            if candidate and candidate.target_job_id == job.id:
                job._has_applied = True
                session = (
                    RankingSession.objects.filter(job=job)
                    .order_by("-created_at")
                    .first()
                )
                if session:
                    cr = CandidateRanking.objects.filter(
                        session=session, candidate=candidate
                    ).first()
                    if cr:
                        job._my_score = cr.ai_score
                        job._my_status = cr.human_decision

        serializer = self.get_serializer(jobs_list, many=True)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Job detail (public info — auth required)
# ---------------------------------------------------------------------------

class JobDetailView(generics.RetrieveAPIView):
    """
    Get detailed job information. Auth required.
    For candidate-specific application info use GET /api/jobs/<id>/apply-info/
    """
    serializer_class = JobSerializer
    queryset = Job.objects.all()
    permission_classes = [OptionalAuth]


# ---------------------------------------------------------------------------
# Recruiter-only: create / update / delete
# ---------------------------------------------------------------------------

class JobCreateView(generics.CreateAPIView):
    """
    Create a new job posting. Recruiter only.
    """
    serializer_class = JobCreateSerializer
    permission_classes = [OptionalAuth, IsRecruiter]

    def perform_create(self, serializer):
        actor = get_api_actor(self.request)
        job = serializer.save(created_by=actor)

        try:
            embedding_service = EmbeddingService()
            job_text = f"{job.title}\n{job.description}\n{job.requirements}"
            embedding, used_openai = embedding_service.generate_job_embedding(job_text)
            job.embedding_vector = embedding
            job.save()
            logger.info(
                "Generated embedding for job %s using %s",
                job.title,
                "OpenAI" if used_openai else "dummy",
            )
        except Exception as e:
            logger.warning("Failed to generate embedding for job %s: %s", job.title, e)

        AuditLog.log_action(
            user=actor,
            action_type="create",
            description=f"Created job posting: {job.title}",
            content_object=job,
            risk_level="medium",
            ip_address=self.request.META.get("REMOTE_ADDR"),
        )


class JobUpdateView(generics.UpdateAPIView):
    """
    Update job information. Recruiter only.
    """
    serializer_class = JobUpdateSerializer
    queryset = Job.objects.all()
    permission_classes = [OptionalAuth, IsRecruiter]

    def perform_update(self, serializer):
        job = serializer.save()

        if "description" in serializer.validated_data or "requirements" in serializer.validated_data:
            try:
                embedding_service = EmbeddingService()
                job_text = f"{job.title}\n{job.description}\n{job.requirements}"
                embedding, used_openai = embedding_service.generate_job_embedding(job_text)
                job.embedding_vector = embedding
                job.save()
                logger.info("Regenerated embedding for job %s", job.title)
            except Exception as e:
                logger.warning("Failed to regenerate embedding for job %s: %s", job.title, e)

        AuditLog.log_action(
            user=get_api_actor(self.request),
            action_type="update",
            description=f"Updated job posting: {job.title}",
            content_object=job,
            risk_level="low",
            ip_address=self.request.META.get("REMOTE_ADDR"),
        )


class JobDeleteView(generics.DestroyAPIView):
    """
    Delete (deactivate) a job posting. Recruiter only.
    """
    queryset = Job.objects.all()
    permission_classes = [OptionalAuth, IsRecruiter]

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()

        AuditLog.log_action(
            user=get_api_actor(self.request),
            action_type="delete",
            description=f"Deactivated job posting: {instance.title}",
            content_object=instance,
            risk_level="medium",
            ip_address=self.request.META.get("REMOTE_ADDR"),
        )
