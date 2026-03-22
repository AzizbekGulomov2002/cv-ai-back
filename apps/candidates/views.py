"""
Views for candidate management and CV processing.
"""
import logging
import os
import re

from rest_framework import generics, status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.audit.models import AuditLog
from services.api_actor import get_api_actor
from services.embedding_service import EmbeddingService
from services.openai_cv_extract_service import extract_structured_profile_from_cv_text
from services.parser_service import CVParserService
from .models import Candidate
from .serializers import (
    CandidateDetailSerializer,
    CandidateSerializer,
    CandidateUpdateSerializer,
    CandidateUploadSerializer,
)

logger = logging.getLogger(__name__)


def _apply_profile_dict_to_candidate(candidate: Candidate, profile: dict) -> None:
    """Map structured profile (OpenAI or heuristic) onto Candidate (not saved)."""
    if not profile:
        return

    fn = (profile.get("full_name") or profile.get("name") or "").strip()
    if fn:
        candidate.name = fn[:200]

    em = (profile.get("email") or "").strip()
    if em:
        candidate.email = em[:254]

    ph = (profile.get("phone") or "").strip()
    if ph:
        ph_clean = re.sub(r"\s+", "", ph)[:15]
        candidate.phone = ph_clean

    sk = profile.get("skills")
    if isinstance(sk, list):
        candidate.skills = [str(x).strip() for x in sk if str(x).strip()][:60]
    elif isinstance(sk, str) and sk.strip():
        candidate.skills = [s.strip() for s in re.split(r"[,;]", sk) if s.strip()][:60]

    yr = profile.get("years_of_experience")
    if yr is not None:
        try:
            candidate.experience_years = max(0, min(80, int(yr)))
        except (TypeError, ValueError):
            pass

    edu = profile.get("education_summary") or profile.get("education")
    if edu:
        candidate.education = str(edu)[:10000]

    candidate.ai_profile_json = profile


def _ensure_required_identity(candidate: Candidate, basename: str) -> None:
    """Guarantee non-empty name/email for display and constraints."""
    parser = CVParserService()
    if not (candidate.name or "").strip():
        guessed = parser.extract_candidate_name(candidate.extracted_text or "", basename)
        candidate.name = (guessed or f"Candidate #{candidate.pk}")[:200]
    if not (candidate.email or "").strip():
        candidate.email = f"candidate-{candidate.pk}@no-email.cv-ai.local"[:254]


def _embedding_input_text(candidate: Candidate) -> str:
    parts = [candidate.extracted_text or ""]
    aj = candidate.ai_profile_json or {}
    summ = aj.get("professional_summary")
    if summ:
        parts.append(str(summ))
    return "\n\n".join(p for p in parts if p).strip()


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def upload_cv(request):
    """
    Upload a CV file. Text is extracted locally; **OpenAI** returns structured JSON
    (name, email, skills, …) which is saved on the candidate. No manual name/email required.
    """
    if request.FILES:
        data = request.POST.copy()
        for key in request.FILES:
            data[key] = request.FILES[key]
    else:
        data = request.data

    serializer = CandidateUploadSerializer(data=data)

    if not serializer.is_valid():
        return Response(
            {"error": "Invalid upload data", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        actor = get_api_actor(request)
        candidate = serializer.save(uploaded_by=actor)
        basename = os.path.basename(candidate.cv_file.name)

        AuditLog.log_cv_upload(
            user=actor,
            candidate=candidate,
            metadata={
                "file_name": candidate.cv_file.name,
                "file_size": candidate.cv_file.size,
            },
            ip_address=request.META.get("REMOTE_ADDR"),
        )

        parser_service = CVParserService()

        try:
            raw_text = parser_service.extract_text(candidate.cv_file.path)
        except Exception as e:
            logger.error("Text extraction failed: %s", e)
            return Response(
                {
                    "message": "Could not read CV file",
                    "candidate": CandidateSerializer(candidate).data,
                    "error": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (raw_text or "").strip():
            return Response(
                {
                    "message": "No text extracted from file (scanned PDF?)",
                    "candidate": CandidateSerializer(candidate).data,
                    "error": "empty_text",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        candidate.extracted_text = raw_text

        profile = extract_structured_profile_from_cv_text(raw_text)
        extraction_source = "openai"

        if not profile:
            extraction_source = "heuristic"
            profile = {
                "full_name": parser_service.extract_candidate_name(raw_text, basename),
                "email": parser_service.extract_email(raw_text),
                "phone": parser_service.extract_phone(raw_text),
                "skills": parser_service.extract_skills(raw_text),
                "years_of_experience": parser_service.extract_experience_years(raw_text),
                "education_summary": parser_service.extract_education(raw_text) or None,
                "professional_summary": None,
                "source": "heuristic_fallback_no_openai",
            }

        _apply_profile_dict_to_candidate(candidate, profile)
        _ensure_required_identity(candidate, basename)
        candidate.save()

        embedding_generated = False
        embed_text = _embedding_input_text(candidate)
        if embed_text:
            try:
                embedding_service = EmbeddingService()
                embedding, used_openai = embedding_service.generate_cv_embedding(embed_text)
                candidate.embedding_vector = embedding
                candidate.save(
                    update_fields=["embedding_vector", "updated_at"]
                )
                embedding_generated = bool(candidate.embedding_vector)
                logger.info(
                    "Embedding for candidate %s via %s",
                    candidate.pk,
                    "OpenAI" if used_openai else "dummy",
                )
            except Exception as e:
                logger.warning("Embedding failed: %s", e)

        return Response(
            {
                "message": "CV processed successfully",
                "extraction_source": extraction_source,
                "candidate": CandidateSerializer(candidate).data,
                "details": {
                    "embedding_generated": embedding_generated,
                    "text_length": len(raw_text),
                },
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        logger.exception("CV upload failed: %s", e)
        return Response(
            {"error": "CV upload failed", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class CandidateListView(generics.ListAPIView):
    """
    List all active candidates.
    """
    serializer_class = CandidateSerializer

    def get_queryset(self):
        queryset = Candidate.objects.filter(is_active=True)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                name__icontains=search
            ) | queryset.filter(
                email__icontains=search
            )

        min_experience = self.request.query_params.get('min_experience')
        if min_experience:
            try:
                min_exp = int(min_experience)
                queryset = queryset.filter(experience_years__gte=min_exp)
            except ValueError:
                pass

        # skills is JSONField — avoid DB-specific icontains; optional filter omitted for SQLite compatibility

        return queryset.order_by('-created_at')


class CandidateDetailView(generics.RetrieveAPIView):
    """
    Get detailed candidate information.
    """
    serializer_class = CandidateDetailSerializer
    queryset = Candidate.objects.all()


class CandidateUpdateView(generics.UpdateAPIView):
    """
    Update candidate information.
    """
    serializer_class = CandidateUpdateSerializer
    queryset = Candidate.objects.all()

    def perform_update(self, serializer):
        candidate = serializer.save()
        AuditLog.log_action(
            user=get_api_actor(self.request),
            action_type='update',
            description=f"Updated candidate {candidate.name}",
            content_object=candidate,
            risk_level='low',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )


class CandidateDeleteView(generics.DestroyAPIView):
    """
    Delete (deactivate) a candidate.
    """
    queryset = Candidate.objects.all()

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()
        AuditLog.log_action(
            user=get_api_actor(self.request),
            action_type='delete',
            description=f"Deactivated candidate {instance.name}",
            content_object=instance,
            risk_level='medium',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
