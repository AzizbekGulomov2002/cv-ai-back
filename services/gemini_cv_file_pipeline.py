"""
CV faylini (PDF/DOCX) Google Gemini ga yuborib, strukturalangan JSON qaytarish.

``google-generativeai``: Files API + ``generate_content`` (AI Studio bepul tier).
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict

from django.conf import settings

from services.cv_json_shared import JSON_INSTRUCTIONS, parse_json_loose

logger = logging.getLogger(__name__)

try:
    import warnings

    # Paket eskirgan deb ogohlantiradi; import paytidagi FutureWarning ni yashirish
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        import google.generativeai as genai
except ImportError:
    genai = None

# Birinchi model 404 bo‘lsa ketma-ket sinash (Google model nomlari tez-tez yangilanadi)
_GEMINI_MODEL_FALLBACKS = (
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-3-flash-preview",
)

_MIME_BY_SUFFIX = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _is_model_not_found_error(exc: BaseException) -> bool:
    """Eski/yo‘q model — boshqa model bilan qayta urinish."""
    try:
        from google.api_core import exceptions as google_exc

        if isinstance(exc, google_exc.NotFound):
            return True
    except ImportError:
        pass
    low = str(exc).lower()
    return "not found" in low and "model" in low


def _gemini_response_text(response: Any) -> str:
    """SDK javobidan matn olish (ba'zan ``response.text`` bloklangan)."""
    t = getattr(response, "text", None)
    if isinstance(t, str) and t.strip():
        return t.strip()
    cands = getattr(response, "candidates", None) or []
    for c in cands:
        content = getattr(c, "content", None)
        parts = getattr(content, "parts", None) if content else None
        if not parts:
            continue
        for p in parts:
            txt = getattr(p, "text", None)
            if txt:
                return str(txt).strip()
    return ""


def extract_with_gemini_file(file_path: str) -> Dict[str, Any]:
    """
    PDF/DOCX ni Gemini ga yuboradi, JSON profil qaytaradi.

    ``GEMINI_API_KEY`` yoki ``GOOGLE_API_KEY`` kerak. Model: ``GEMINI_CV_MODEL``
    (sukut: ``gemini-2.5-flash``; 404 bo‘lsa zaxira modellar sinanadi).
    """
    api_key = (
        (getattr(settings, "GEMINI_API_KEY", None) or "")
        or (getattr(settings, "GOOGLE_API_KEY", None) or "")
    ).strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY (yoki GOOGLE_API_KEY) sozlanmagan.")

    if genai is None:
        raise RuntimeError("google-generativeai o‘rnatilmagan: pip install google-generativeai")

    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"CV fayl topilmadi: {file_path}")

    suffix = path.suffix.lower()
    if suffix not in (".pdf", ".docx"):
        raise ValueError(f"Qo‘llab-quvvatlanmaydigan format: {suffix}")

    mime = _MIME_BY_SUFFIX.get(suffix)
    primary = (getattr(settings, "GEMINI_CV_MODEL", None) or "gemini-2.5-flash").strip()
    seen: set[str] = set()
    model_candidates: list[str] = []
    for m in (primary, *_GEMINI_MODEL_FALLBACKS):
        if m and m not in seen:
            seen.add(m)
            model_candidates.append(m)

    genai.configure(api_key=api_key)
    uploaded: Any = None

    try:
        uploaded = genai.upload_file(
            path=str(path),
            mime_type=mime,
        )
        # Fayl tayyor bo‘lguncha kutish
        while uploaded.state.name == "PROCESSING":
            time.sleep(1)
            uploaded = genai.get_file(uploaded.name)
        if uploaded.state.name == "FAILED":
            raise RuntimeError("Gemini faylni qayta ishlashda xato (FAILED).")

        last_err: BaseException | None = None
        for model_name in model_candidates:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content([JSON_INSTRUCTIONS, uploaded])
                raw = _gemini_response_text(response)
                if not raw:
                    raise RuntimeError("Gemini bo‘sh javob qaytardi.")

                data = parse_json_loose(raw)
                if not isinstance(data, dict):
                    raise ValueError("Gemini javobi JSON obyekt emas.")

                data["source"] = "gemini_file_api"
                data["gemini_model"] = model_name
                if model_name != primary:
                    logger.info(
                        "Gemini: asosiy model `%s` o‘rniga `%s` ishlatildi.",
                        primary,
                        model_name,
                    )
                return data
            except Exception as e:
                last_err = e
                if _is_model_not_found_error(e) and model_name != model_candidates[-1]:
                    logger.warning(
                        "Gemini model `%s` mavjud emas yoki generateContent qo‘llab-quvvatlamaydi: %s",
                        model_name,
                        e,
                    )
                    continue
                raise

        if last_err is not None:
            raise last_err
        raise RuntimeError("Hech qanday Gemini model sinab ko‘rilmadi.")
    finally:
        if uploaded is not None and genai is not None:
            try:
                genai.delete_file(uploaded.name)
            except Exception as e:
                logger.warning("Gemini faylini o‘chirishda xato (e’tiborsiz): %s", e)
