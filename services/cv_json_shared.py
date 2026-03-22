"""
CV dan JSON ajratish uchun umumiy prompt va parser (OpenAI / Gemini).

EU AI Act / yuqori xavfli recruiting AI uchun shaffoflik: fairness_scan, compliance, skill_evidence.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict

JSON_INSTRUCTIONS = """You are a CV parser for a recruitment decision-support system (EU high-risk AI context).
Read the attached CV file (PDF or Word). You ONLY extract and structure facts from the document.

Return exactly ONE JSON object (no markdown fences) with these keys:

CORE (required):
- full_name: string or null
- email: string or null
- phone: string or null
- skills: array of strings (max 40)
- years_of_experience: integer or null (infer only from explicit dates/tenure in the CV, else null)
- education_summary: string or null
- professional_summary: string or null — 2–4 factual sentences on role, domain, seniority (from CV only)
- embedding_text: string — rich text for semantic search: roles, tools, achievements, education (no invented facts)

FAIRNESS & TRANSPARENCY (required objects; use false/null/[] when not applicable):
- fairness_scan: object:
  - gender_proxy_detected: boolean — true only if CV contains explicit gender markers (pronouns about self, gendered titles like Mr/Mrs in contact, explicit gender words). false if absent or unclear.
  - gender_proxy_notes: string or null — neutral one-line note (e.g. "Third-person bio uses he/him") or null
  - age_proxy_detected: boolean — true if explicit age, birth year, or "born in YYYY" appears
  - age_proxy_notes: string or null
  - other_proxy_flags: array of strings — e.g. "marital_status", "photo_reference", "nationality_stated" if explicitly present; else []
- compliance: object:
  - factors_used_for_profile: array of strings — e.g. "skills", "employment_history", "education", "years_of_experience"
  - factors_not_used_for_automated_decision: array of strings — always include at least "gender", "age", "ethnicity", "religion" as NOT used for scoring (system policy)
  - limitation_note: string — one sentence on OCR/PDF limits or missing sections

SKILL EVIDENCE (required array, may be empty):
- skill_evidence: array of up to 15 objects, each { "skill": string, "evidence": string } — "evidence" must be a short paraphrase or phrase grounded in the CV (not invented). Match skills from your skills list where possible.

Rules:
- Do not invent email/phone/employers/dates not present in the document. Use null when unknown.
- This JSON is for HR transparency; do not output hiring decisions (no "hire/reject")."""


def parse_json_loose(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
    return json.loads(text)


def normalize_llm_profile(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Eski modellar yoki qisqa javoblarda yangi kalitlar bo‘lmasa, sukut obyektlar qo‘shish.
    """
    if not isinstance(data, dict):
        return {}
    out = dict(data)
    if not isinstance(out.get("fairness_scan"), dict):
        out["fairness_scan"] = {
            "gender_proxy_detected": False,
            "gender_proxy_notes": None,
            "age_proxy_detected": False,
            "age_proxy_notes": None,
            "other_proxy_flags": [],
        }
    if not isinstance(out.get("compliance"), dict):
        out["compliance"] = {
            "factors_used_for_profile": ["skills", "education", "experience_text"],
            "factors_not_used_for_automated_decision": [
                "gender",
                "age",
                "ethnicity",
                "religion",
            ],
            "limitation_note": "Structured extraction may miss scanned or unusual PDF layouts.",
        }
    if not isinstance(out.get("skill_evidence"), list):
        out["skill_evidence"] = []
    return out
