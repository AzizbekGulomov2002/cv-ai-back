"""
Job ↔ candidate frontend-ready payload (upload va boshqa endpointlar uchun).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from apps.candidates.models import Candidate
from apps.jobs.models import Job
from apps.ranking.models import CandidateRanking, RankingSession
from apps.ranking.rank_utils import leaderboard_rank_score_100


def _norm_skill(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower().strip())


def _tokens(s: str) -> set[str]:
    return {t for t in re.split(r"[/,\s]+", _norm_skill(s)) if len(t) > 1}


def skill_match_score(required: str, candidate_skills: List[str]) -> float:
    """0.0–1.0: aniq moslik / qisman / yo‘q."""
    req = _norm_skill(required)
    if not req:
        return 0.0
    req_tokens = _tokens(required)
    best = 0.0
    for c in candidate_skills:
        cn = _norm_skill(str(c))
        if not cn:
            continue
        if req == cn:
            return 1.0
        if req in cn or cn in req:
            best = max(best, 0.88)
            continue
        ct = _tokens(c)
        if req_tokens and ct:
            inter = req_tokens & ct
            union = req_tokens | ct
            j = len(inter) / len(union) if union else 0.0
            if j >= 0.5:
                best = max(best, 0.55 + 0.35 * j)
    return round(min(1.0, best), 2)


def build_skill_breakdown(job: Job, candidate: Candidate) -> Dict[str, float]:
    """Job required + preferred skill nomlari → 0..1 ball."""
    seen: List[str] = []
    for s in (job.required_skills or []) + (job.preferred_skills or []):
        t = str(s).strip()
        if t and t not in seen:
            seen.append(t)
    skills = candidate.skills or []
    return {name: skill_match_score(name, skills) for name in seen}


def required_skills_coverage_percent(breakdown: Dict[str, float], job: Job) -> Optional[float]:
    req = [str(s).strip() for s in (job.required_skills or []) if str(s).strip()]
    if not req:
        return None
    acc = 0.0
    for r in req:
        v = breakdown.get(r)
        if v is None:
            v = 0.0
        acc += float(v)
    return round(100.0 * acc / len(req), 1)


def candidate_short_dict(candidate: Candidate) -> Dict[str, Any]:
    return {
        "id": candidate.pk,
        "name": candidate.name or "",
        "experience_years": candidate.experience_years,
        "skills": list(candidate.skills or []),
    }


def get_ranking_context(candidate: Candidate, job: Job) -> Tuple[Optional[int], int, bool]:
    """
    (rank_position, total_candidates, from_session)
    rank_position = ai_rank (1-based). ``rank`` 0–100 uchun ``leaderboard_rank_score_100`` ishlating.
    Agar so‘nggi sessiyada nomzod bo‘lmasa: rank_position=None, total=active count, from_session=False
    """
    total_active = Candidate.objects.filter(is_active=True).count()
    session = (
        RankingSession.objects.filter(job=job).order_by("-created_at").first()
    )
    if not session:
        return None, total_active, False
    cr = CandidateRanking.objects.filter(session=session, candidate=candidate).first()
    n_ranked = CandidateRanking.objects.filter(session=session).count()
    total = n_ranked or session.candidates_count or total_active
    if not cr:
        return None, total, False
    return cr.ai_rank, total, True


def build_explanation_block(
    ev: Dict[str, Any],
    candidate: Candidate,
    job: Job,
) -> Dict[str, str]:
    composite = float(ev.get("score", 0))
    prof = (candidate.professional_summary or "").strip()
    summary = (
        f"Match {composite:.0f}/100 vs «{job.title}» ({job.company}). "
        f"Recommendation only — HR decides (EU AI Act decision-support)."
    )
    if prof:
        summary = f"{summary} Profile: {prof[:200]}{'…' if len(prof) > 200 else ''}"

    details_parts: List[str] = []
    mb = ev.get("match_breakdown") or {}
    for d in mb.get("dimensions", [])[:5]:
        label = d.get("label", d.get("id", ""))
        expl = d.get("explanation", "")
        sc = d.get("score", 0)
        details_parts.append(f"{label} ({float(sc):.0f}/100): {expl}")
    if not details_parts:
        details_parts.append(ev.get("explanation", "")[:2000])
    details = "\n\n".join(details_parts)
    return {"summary": summary, "details": details}


def build_fairness_block(
    candidate: Candidate,
    bias_flags: List[str],
) -> Dict[str, Any]:
    fs = candidate.fairness_scan_json or {}
    if not isinstance(fs, dict):
        fs = {}
    proxy = bool(fs.get("gender_proxy_detected")) or bool(fs.get("age_proxy_detected"))
    bias_heuristic = bool(bias_flags)
    notes: Optional[str] = None
    parts = []
    if fs.get("gender_proxy_notes"):
        parts.append(f"Gender-related text note: {fs['gender_proxy_notes']}")
    if fs.get("age_proxy_notes"):
        parts.append(f"Age-related text note: {fs['age_proxy_notes']}")
    if bias_flags:
        parts.append("Heuristic flags: " + ", ".join(bias_flags[:8]))
    if parts:
        notes = " | ".join(parts)
    return {
        "bias_detected": proxy or bias_heuristic,
        "proxy_in_cv": proxy,
        "heuristic_flags": bias_heuristic,
        "notes": notes,
    }


def build_audit_block(profile: Dict[str, Any]) -> Dict[str, Any]:
    src = profile.get("source") or "unknown"
    model_parts = [src]
    if profile.get("openai_model"):
        model_parts.append(str(profile["openai_model"]))
    if profile.get("gemini_model"):
        model_parts.append(str(profile["gemini_model"]))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "model": "embedding_similarity_v1+dimensions",
        "extraction": "+".join(model_parts),
    }


def format_frontend_job_bundle(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Frontend ideal struktura: candidate, ranking, matching (skill_match = skill_breakdown),
    explanation, fairness (faqat bias_detected + notes), audit (model nomi qisqa).
    """
    r = raw.get("ranking") or {}
    m = raw.get("matching") or {}
    sb = dict(m.get("skill_breakdown") or {})
    fair = raw.get("fairness") or {}
    aud = raw.get("audit") or {}
    notes = fair.get("notes")
    return {
        "candidate": raw.get("candidate") or {},
        "job": raw.get("job"),
        "ranking": {
            "score": r.get("score", 0),
            "rank": r.get("rank"),
            "rank_position": r.get("rank_position"),
            "total_candidates": r.get("total_candidates", 0),
        },
        "matching": {
            "skills_match_percentage": m.get("skills_match_percentage"),
            "matched_skills": list(m.get("matched_skills") or []),
            "missing_skills": list(m.get("missing_skills") or []),
            "skill_breakdown": sb,
            "skill_match": sb,
            "match_breakdown": m.get("match_breakdown") or {},
        },
        "explanation": raw.get("explanation") or {"summary": "", "details": ""},
        "fairness": {
            "bias_detected": bool(fair.get("bias_detected")),
            "notes": notes if notes else None,
        },
        "audit": {
            "generated_at": aud.get("generated_at"),
            "model": "embedding_similarity_v1",
        },
    }


def build_job_evaluation_payload(
    candidate: Candidate,
    job: Job,
    profile: Dict[str, Any],
    ev: Dict[str, Any],
) -> Dict[str, Any]:
    """Frontend-ready «candidate vs job» — foydalanuvchi so‘ragan root strukturaga mos."""
    skill_breakdown = build_skill_breakdown(job, candidate)
    matched = list(ev.get("matched_skills") or [])
    missing = list(ev.get("missing_skills") or [])
    cov = required_skills_coverage_percent(skill_breakdown, job)
    rank_pos, total, from_sess = get_ranking_context(candidate, job)
    rank_0_100 = None
    if rank_pos is not None and total and from_sess:
        rank_0_100 = leaderboard_rank_score_100(rank_pos, total)

    explanation = build_explanation_block(ev, candidate, job)
    fairness = build_fairness_block(candidate, list(ev.get("bias_flags") or []))
    audit = build_audit_block(profile)

    return {
        "candidate": candidate_short_dict(candidate),
        "job": {"id": job.id, "title": job.title, "company": job.company},
        "ranking": {
            "score": round(float(ev.get("score", 0)), 2),
            "rank": rank_0_100,
            "rank_position": rank_pos,
            "total_candidates": total,
            "leaderboard_from_latest_session": from_sess,
        },
        "matching": {
            "skills_match_percentage": cov,
            "matched_skills": matched,
            "missing_skills": missing,
            "skill_breakdown": skill_breakdown,
            "match_breakdown": ev.get("match_breakdown") or {},
        },
        "explanation": explanation,
        "fairness": fairness,
        "audit": audit,
    }
