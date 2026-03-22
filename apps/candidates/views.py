"""
Views for candidate management and CV processing.
"""
import logging
import os
import re

from django.conf import settings
from rest_framework import generics, status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.audit.models import AuditLog
from services.api_actor import get_api_actor
from services.embedding_service import EmbeddingService
from services.cv_file_extract import extract_structured_profile_from_cv_file
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
    """Map structured profile (OpenAI JSON) onto Candidate (not saved)."""
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
    """Bo‘sh ism/email bo‘lsa minimal to‘ldirish."""
    parser = CVParserService()
    if not (candidate.name or "").strip():
        guessed = parser.extract_candidate_name(candidate.extracted_text or "", basename)
        candidate.name = (guessed or f"Candidate #{candidate.pk}")[:200]
    if not (candidate.email or "").strip():
        candidate.email = f"candidate-{candidate.pk}@no-email.cv-ai.local"[:254]


def _cv_core_fields_from_profile(profile: dict) -> dict:
    """LLM JSON dan frontend uchun asosiy maydonlar (model/source kalitlari siz)."""
    if not profile:
        return {}
    keys = (
        "full_name",
        "email",
        "phone",
        "skills",
        "years_of_experience",
        "education_summary",
        "professional_summary",
        "embedding_text",
    )
    return {k: profile.get(k) for k in keys}


def _extraction_meta_from_profile(profile: dict) -> dict:
    """Qaysi provayder / model ishlatilgani."""
    if not profile:
        return {}
    meta = {"source": profile.get("source")}
    if profile.get("openai_model"):
        meta["openai_model"] = profile.get("openai_model")
    if profile.get("gemini_model"):
        meta["gemini_model"] = profile.get("gemini_model")
    return meta


def _embedding_input_from_profile(profile: dict, candidate: Candidate) -> str:
    """Embedding uchun matn — OpenAI qaytargan embedding_text yoki maydonlardan yig‘indi."""
    et = (profile or {}).get("embedding_text") or ""
    if isinstance(et, str) and et.strip():
        return et.strip()[:50000]
    parts = [
        candidate.extracted_text or "",
        (profile or {}).get("professional_summary"),
        (profile or {}).get("education_summary"),
        " ".join((profile or {}).get("skills") or []),
    ]
    return "\n\n".join(p for p in parts if p).strip()[:50000]


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def upload_cv(request):
    """
    CV faylini yuklash. PDF/DOCX **lokal tahlil qilinmaydi** — fayl OpenAI yoki Gemini
    orqali yuboriladi (``CV_EXTRACT_PROVIDER``), JSON natija saqlanadi.
    Kamida bittasi kerak: ``OPENAI_API_KEY`` yoki ``GEMINI_API_KEY`` / ``GOOGLE_API_KEY``.
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

        openai_key = (getattr(settings, "OPENAI_API_KEY", None) or "").strip()
        gemini_key = (
            (getattr(settings, "GEMINI_API_KEY", None) or "")
            or (getattr(settings, "GOOGLE_API_KEY", None) or "")
        ).strip()
        if not openai_key and not gemini_key:
            return Response(
                {
                    "message": "Serverda OPENAI_API_KEY yoki GEMINI_API_KEY sozlanmagan — CV fayl bulut orqali o‘qiladi.",
                    "candidate": CandidateSerializer(candidate).data,
                    "error": "missing_llm_key",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        profile = extract_structured_profile_from_cv_file(candidate.cv_file.path)
        if not profile:
            return Response(
                {
                    "message": "CV tahlili muvaffaqiyatsiz (OpenAI/Gemini — loglarni tekshiring).",
                    "candidate": CandidateSerializer(candidate).data,
                    "error": "cv_extraction_failed",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        _apply_profile_dict_to_candidate(candidate, profile)

        candidate.extracted_text = _embedding_input_from_profile(profile, candidate)[:50000]

        _ensure_required_identity(candidate, basename)
        candidate.save()

        embedding_generated = False
        embed_text = _embedding_input_from_profile(profile, candidate)
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

        src = (profile or {}).get("source") or "unknown"
        details = {
            "embedding_generated": embedding_generated,
            "extracted_text_length": len(candidate.extracted_text or ""),
            "extraction_source": src,
        }
        if (profile or {}).get("openai_model"):
            details["openai_model"] = profile.get("openai_model")
        if (profile or {}).get("gemini_model"):
            details["gemini_model"] = profile.get("gemini_model")

        body = {
            "message": "CV processed successfully (file pipeline)",
            "extraction_source": src,
            # To‘liq LLM JSON — DB dagi candidate.ai_profile_json bilan bir xil
            "extracted_profile": profile,
            # Qisqa ko‘rinish (forma / UI uchun)
            "cv_parsed": _cv_core_fields_from_profile(profile),
            "extraction": _extraction_meta_from_profile(profile),
            # Embedding / qidiruv uchun saqlangan matn
            "extracted_text": candidate.extracted_text or "",
            "candidate": CandidateSerializer(candidate).data,
            "details": details,
        }
        if src == "openai_file_responses_api":
            body["openai_model"] = (profile or {}).get("openai_model") or getattr(
                settings, "OPENAI_CV_MODEL", "gpt-4o"
            )
        if (profile or {}).get("gemini_model"):
            body["gemini_model"] = profile.get("gemini_model")

        return Response(body, status=status.HTTP_201_CREATED)

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
