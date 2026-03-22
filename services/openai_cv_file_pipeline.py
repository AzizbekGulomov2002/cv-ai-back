"""
CV faylini (PDF/DOCX) lokal o‘qimagan holda OpenAI ga yuborib, strukturalangan JSON qaytarish.

OpenAI Files API (`purpose=user_data`) + Responses API (`input_file`) — rasmiy yo‘l.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from django.conf import settings

from services.cv_json_shared import JSON_INSTRUCTIONS, parse_json_loose

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def _extract_responses_output_text(response: Any) -> str:
    """SDK versiyalarida ``output_text`` yoki ``output`` dan matn olish."""
    t = getattr(response, "output_text", None)
    if isinstance(t, str) and t.strip():
        return t
    out = getattr(response, "output", None) or []
    chunks = []
    for item in out:
        contents = getattr(item, "content", None) or []
        for c in contents:
            ct = getattr(c, "type", "") or ""
            if ct in ("output_text", "text"):
                txt = getattr(c, "text", None)
                if txt:
                    chunks.append(txt)
            elif isinstance(c, dict):
                if c.get("type") in ("output_text", "text") and c.get("text"):
                    chunks.append(c["text"])
    return "\n".join(chunks).strip()


def extract_with_openai_file(file_path: str) -> Dict[str, Any]:
    """
    PDF/DOCX faylni OpenAI ga yuboradi, JSON profil qaytaradi.

    ``OPENAI_API_KEY`` bo‘lishi shart. Model: ``OPENAI_CV_MODEL`` (tavsiya: ``gpt-4o``).

    Xatolarda exception ko‘taradi (fallback uchun ``cv_file_extract`` ishlatiladi).
    """
    api_key = getattr(settings, "OPENAI_API_KEY", None) or ""
    if not api_key.strip():
        raise RuntimeError("OPENAI_API_KEY sozlanmagan.")

    if OpenAI is None:
        raise RuntimeError("openai paketi o‘rnatilmagan.")

    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"CV fayl topilmadi: {file_path}")

    suffix = path.suffix.lower()
    if suffix not in (".pdf", ".docx"):
        raise ValueError(f"Qo‘llab-quvvatlanmaydigan format: {suffix}")

    model = getattr(settings, "OPENAI_CV_MODEL", None) or "gpt-4o"

    client: Any = None
    uploaded: Any = None

    try:
        client = OpenAI(api_key=api_key)
        with open(path, "rb") as fh:
            uploaded = client.files.create(file=fh, purpose="user_data")

        if not hasattr(client, "responses"):
            raise RuntimeError(
                "OpenAI Python SDK juda eski: pip install -U 'openai>=1.40.0' "
                "(Responses API kerak)."
            )

        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_file", "file_id": uploaded.id},
                        {"type": "input_text", "text": JSON_INSTRUCTIONS},
                    ],
                }
            ],
        )

        raw = _extract_responses_output_text(response)
        data = parse_json_loose(raw)
        if not isinstance(data, dict):
            raise ValueError("OpenAI javobi JSON obyekt emas.")

        data["source"] = "openai_file_responses_api"
        data["openai_model"] = model
        return data

    except json.JSONDecodeError as e:
        logger.exception("OpenAI javobi JSON emas: %s", e)
        raise
    finally:
        if client is not None and uploaded is not None:
            try:
                client.files.delete(uploaded.id)
            except Exception as e:
                logger.warning("OpenAI faylini o‘chirishda xato (e’tiborsiz): %s", e)


def extract_structured_profile_from_cv_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Eski API: faqat OpenAI, xatolarda ``None``.

    Yangi kod ``services.cv_file_extract.extract_structured_profile_from_cv_file`` dan foydalansin.
    """
    try:
        return extract_with_openai_file(file_path)
    except Exception as e:
        logger.exception("OpenAI file pipeline xato: %s", e)
        return None
