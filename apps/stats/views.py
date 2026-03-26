"""
Recruiter dashboard statistics views.
All endpoints require role=recruiter.
"""
import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.users.permissions import IsRecruiter
from services.stats_service import StatsService

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsRecruiter])
def recruiter_dashboard(request):
    """
    Full recruiter statistics dashboard.

    Query params:
      days (int, default 30) — look-back window for trend data

    Returns:
      overview        — total counts (jobs, candidates, rankings, scores)
      pipeline        — funnel: pending → shortlisted → accepted / rejected with %
      per_job         — per-job breakdown: applicants, avg/max/min score, decisions, emails
      score_distribution — histogram by 20-point buckets
      skills_gap      — top 15 most missing / most matched skills across all rankings
      trends          — candidates uploaded per day + ranking sessions per day
      top_candidates  — top 10 highest AI scores with decision status
      users           — recruiter/candidate account counts
      emails          — accept/reject emails sent, pending notifications
    """
    try:
        days_raw = request.query_params.get("days", "30")
        try:
            days = max(1, min(int(days_raw), 365))
        except (TypeError, ValueError):
            days = 30

        service = StatsService()
        data = service.get_dashboard(days=days)

        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception("Stats dashboard failed: %s", e)
        return Response(
            {"error": "Failed to generate statistics.", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsRecruiter])
def job_stats_detail(request, job_id):
    """
    Detailed statistics for a single job.
    Includes: all rankings, score breakdown, skills gap, email stats.
    """
    from apps.jobs.models import Job
    from apps.candidates.models import Candidate
    from apps.ranking.models import CandidateRanking, RankingSession
    from django.db.models import Avg, Count, Max, Min

    job = Job.objects.filter(pk=job_id).first()
    if not job:
        return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

    applicants_count = Candidate.objects.filter(
        target_job=job, is_active=True
    ).count()

    sessions = list(
        RankingSession.objects.filter(job=job).order_by("-created_at")
    )

    sessions_data = []
    all_rankings = []
    for session in sessions:
        rankings_qs = CandidateRanking.objects.filter(session=session).select_related(
            "candidate"
        )
        agg = rankings_qs.aggregate(
            cnt=Count("id"),
            avg=Avg("ai_score"),
            hi=Max("ai_score"),
            lo=Min("ai_score"),
        )
        decisions = {}
        for row in rankings_qs.values("human_decision").annotate(cnt=Count("id")):
            decisions[row["human_decision"]] = row["cnt"]

        session_info = {
            "session_id": session.id,
            "created_at": session.created_at.isoformat(),
            "candidates_count": agg["cnt"] or 0,
            "avg_score": round(agg["avg"] or 0, 2),
            "max_score": round(agg["hi"] or 0, 2),
            "min_score": round(agg["lo"] or 0, 2),
            "decisions": decisions,
            "email_sent": rankings_qs.filter(email_sent=True).count(),
        }
        sessions_data.append(session_info)
        all_rankings.extend(list(rankings_qs))

    # Rankings list (latest session)
    latest_rankings = []
    if sessions:
        latest_qs = CandidateRanking.objects.filter(
            session=sessions[0]
        ).select_related("candidate").order_by("ai_rank")
        for cr in latest_qs:
            mb = cr.match_breakdown if isinstance(cr.match_breakdown, dict) else {}
            latest_rankings.append(
                {
                    "ranking_id": cr.id,
                    "ai_rank": cr.ai_rank,
                    "rank": float(cr.rank) if cr.rank is not None else float(cr.ai_rank),
                    "candidate_id": cr.candidate.id,
                    "name": cr.candidate.name,
                    "email": cr.candidate.email,
                    "github": cr.candidate.github or None,
                    "ai_score": cr.ai_score,
                    "final_score": cr.final_score,
                    "human_decision": cr.human_decision,
                    "human_score": cr.human_score,
                    "matched_skills": cr.matched_skills,
                    "missing_skills": cr.missing_skills,
                    "scoring_summary": mb.get("scoring_summary"),
                    "email_sent": cr.email_sent,
                    "email_type": cr.email_type,
                    "is_reviewed": cr.is_reviewed,
                }
            )

    # Skills gap for this job
    from collections import Counter
    missing_c: Counter = Counter()
    matched_c: Counter = Counter()
    for cr in all_rankings:
        for s in cr.missing_skills or []:
            if s:
                missing_c[s.strip()] += 1
        for s in cr.matched_skills or []:
            if s:
                matched_c[s.strip()] += 1

    return Response(
        {
            "job": {
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "level": job.level,
                "is_active": job.is_active,
                "required_skills": job.required_skills,
                "preferred_skills": job.preferred_skills,
                "min_experience": job.min_experience,
            },
            "applicants_count": applicants_count,
            "sessions_count": len(sessions),
            "sessions": sessions_data,
            "latest_rankings": latest_rankings,
            "skills_gap": {
                "most_missing": [
                    {"skill": s, "count": c} for s, c in missing_c.most_common(10)
                ],
                "most_matched": [
                    {"skill": s, "count": c} for s, c in matched_c.most_common(10)
                ],
            },
        },
        status=status.HTTP_200_OK,
    )
