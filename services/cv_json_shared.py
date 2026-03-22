"""
CV dan JSON ajratish uchun umumiy prompt va parser (OpenAI / Gemini).
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict

JSON_INSTRUCTIONS = """You are a CV parser. Read the attached CV file (PDF or Word).

Return exactly ONE JSON object (no markdown fences) with these keys:
- full_name: string or null
- email: string or null
- phone: string or null
- skills: array of strings (max 40)
- years_of_experience: integer or null
- education_summary: string or null
- professional_summary: string or null
- embedding_text: string — concatenate the most important CV text (skills, roles, education) for semantic search; at least a few sentences if the CV has content.

Rules: Do not invent email/phone not present in the document. Use null when unknown."""


def parse_json_loose(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
    return json.loads(text)
