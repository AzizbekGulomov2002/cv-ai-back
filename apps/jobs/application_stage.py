"""
High-level application stage for a candidate on a job (no numeric score or rank).
Used in candidate-facing APIs.
"""


def application_stage_for_job(candidate, job):
    """
    Returns None if the candidate is not applied to this job.
    Otherwise: 'received' | 'under_review' | human_decision value (shortlisted, accepted, rejected).
    """
    from apps.ranking.models import CandidateRanking, RankingSession

    if not candidate or not job or candidate.target_job_id != job.id:
        return None
    session = RankingSession.objects.filter(job=job).order_by("-created_at").first()
    if not session:
        return "received"
    cr = CandidateRanking.objects.filter(session=session, candidate=candidate).first()
    if not cr:
        return "received"
    hd = cr.human_decision or "pending"
    if hd == "pending":
        return "under_review"
    return hd
