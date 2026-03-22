"""
Extract structured candidate profile from raw CV text using OpenAI Chat Completions.

Used after local PDF/DOCX text extraction — no manual name/email from the client required.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# Max characters sent to the model (rough token control)
MAX_CV_TEXT_CHARS = 100_000

SYSTEM_PROMPT = """You are a recruitment CV parser. Read the CV text and return ONE JSON object only.
Rules:
- Use UTF-8 strings. If a field is unknown, use null (not empty string) for optional scalars, [] for skills if none.
- skills: list of distinct professional/technical skills (strings), max 40 items.
- years_of_experience: best integer estimate of total professional experience, or null.
- Do not invent contact details that are not implied in the text; if missing, null.
- full_name: person's name as written on the CV header, or null.
"""


def _parse_json_loose(raw: str) -> Dict[str, Any]:
    """Parse model output; strip markdown fences if present."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
    return json.loads(text)


def extract_structured_profile_from_cv_text(cv_text: str) -> Optional[Dict[str, Any]]:
    """
    Call OpenAI to turn raw CV text into a structured dict.

    Returns:
        dict with keys like full_name, email, phone, skills, years_of_experience,
        education_summary, professional_summary — or None if API key missing / call failed.
    """
    api_key = getattr(settings, "OPENAI_API_KEY", None) or ""
    if not api_key.strip():
        logger.info("OPENAI_API_KEY not set; skipping OpenAI CV extraction.")
        return None

    if OpenAI is None:
        logger.error("openai package not installed.")
        return None

    text = (cv_text or "").strip()
    if not text:
        return None

    truncated = text[:MAX_CV_TEXT_CHARS]
    model = getattr(settings, "OPENAI_CV_MODEL", None) or "gpt-4o-mini"

    user_prompt = (
        "Extract structured data from this CV text.\n\n"
        "Required JSON shape:\n"
        "{\n"
        '  "full_name": string|null,\n'
        '  "email": string|null,\n'
        '  "phone": string|null,\n'
        '  "skills": string[],\n'
        '  "years_of_experience": integer|null,\n'
        '  "education_summary": string|null,\n'
        '  "professional_summary": string|null\n'
        "}\n\n"
        f"CV TEXT:\n---\n{truncated}\n---"
    )

    try:
        client = OpenAI(api_key=api_key)
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        # json_object supported on recent models; fallback if API complains
        try:
            kwargs["response_format"] = {"type": "json_object"}
            completion = client.chat.completions.create(**kwargs)
        except Exception as e1:
            logger.warning("OpenAI json_object format failed (%s); retrying without it.", e1)
            kwargs.pop("response_format", None)
            completion = client.chat.completions.create(**kwargs)

        raw = completion.choices[0].message.content or ""
        data = _parse_json_loose(raw)
        if not isinstance(data, dict):
            return None
        return data
    except Exception as e:
        logger.exception("OpenAI CV extraction failed: %s", e)
        return None
