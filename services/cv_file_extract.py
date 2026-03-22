"""
CV faylidan strukturalangan profil: OpenAI yoki Gemini (sozlamaga qarab + auto fallback).

``CV_EXTRACT_PROVIDER``:
- ``auto`` (sukut): avval OpenAI; 429 / quota bo‘lsa — Gemini (agar kalit bo‘lsa).
- ``openai``: faqat OpenAI.
- ``gemini``: faqat Gemini.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from django.conf import settings

from services.gemini_cv_file_pipeline import extract_with_gemini_file
from services.openai_cv_file_pipeline import extract_with_openai_file

logger = logging.getLogger(__name__)


def _should_fallback_to_gemini(exc: BaseException) -> bool:
    """OpenAI quota / rate limit — Gemini ga o‘tish."""
    try:
        from openai import RateLimitError
    except ImportError:
        RateLimitError = ()  # type: ignore

    if RateLimitError and isinstance(exc, RateLimitError):
        return True

    msg = str(exc).lower()
    if "insufficient_quota" in msg:
        return True
    if "429" in msg and ("quota" in msg or "rate" in msg):
        return True

    try:
        from openai import APIStatusError
    except ImportError:
        return False

    if isinstance(exc, APIStatusError) and getattr(exc, "status_code", None) == 429:
        return True
    return False


def extract_structured_profile_from_cv_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    PDF/DOCX dan JSON profil. ``None`` — kalit yo‘q yoki ikkala provayder ham muvaffaqiyatsiz.

    Kalitlar: ``OPENAI_API_KEY``, ``GEMINI_API_KEY`` / ``GOOGLE_API_KEY``.
    """
    provider = (getattr(settings, "CV_EXTRACT_PROVIDER", None) or "auto").strip().lower()
    openai_key = (getattr(settings, "OPENAI_API_KEY", None) or "").strip()
    gemini_key = (
        (getattr(settings, "GEMINI_API_KEY", None) or "")
        or (getattr(settings, "GOOGLE_API_KEY", None) or "")
    ).strip()

    if provider == "openai":
        if not openai_key:
            logger.warning("CV_EXTRACT_PROVIDER=openai lekin OPENAI_API_KEY yo‘q.")
            return None
        try:
            return extract_with_openai_file(file_path)
        except Exception as e:
            logger.exception("OpenAI fayl pipeline xato: %s", e)
            return None

    if provider == "gemini":
        if not gemini_key:
            logger.warning("CV_EXTRACT_PROVIDER=gemini lekin GEMINI_API_KEY yo‘q.")
            return None
        try:
            return extract_with_gemini_file(file_path)
        except Exception as e:
            logger.exception("Gemini fayl pipeline xato: %s", e)
            return None

    # --- auto ---
    if openai_key:
        try:
            return extract_with_openai_file(file_path)
        except Exception as e:
            if _should_fallback_to_gemini(e) and gemini_key:
                logger.warning(
                    "OpenAI cheklovi / quota: %s — Gemini ga o‘tilmoqda.",
                    e,
                )
                try:
                    return extract_with_gemini_file(file_path)
                except Exception as e2:
                    logger.exception("Gemini fallback ham muvaffaqiyatsiz: %s", e2)
                    return None
            logger.exception("OpenAI fayl pipeline xato: %s", e)
            return None

    if gemini_key:
        try:
            return extract_with_gemini_file(file_path)
        except Exception as e:
            logger.exception("Gemini fayl pipeline xato: %s", e)
            return None

    logger.warning("OPENAI_API_KEY va GEMINI_API_KEY ikkalasi ham yo‘q.")
    return None
