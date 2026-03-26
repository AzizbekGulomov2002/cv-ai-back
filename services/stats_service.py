"""
Statistics service for the AI CV System recruiter dashboard.

Logic design:
  - Overview counts (jobs, candidates, sessions, emails)
  - Pipeline by human_decision on ranking rows (pending → shortlisted → accepted / rejected)
  - Candidate funnel for UI (total CVs → qualified / top tier by max ai_score → interview flags)
  - Skill / experience / salary (jobs) / location (target_job) distributions
  - Per-job stats (applicants, avg_score, top_score, decision breakdown)
  - Score distribution histogram
  - Skills gap analysis (most missing & most matched across all rankings)
  - Time trends (candidates uploaded per day, rankings per day) — last N days
  - Top scoring candidates
  - User role breakdown
  - Email notification stats
"""
import logging
from collections import Counter, defaultdict
from datetime import timedelta
from typing import Any, Dict

from django.db.models import Avg, Count, Max, Min, Q
from django.utils import timezone

logger = logging.getLogger(__name__)


class StatsService:
    """
    Generates comprehensive recruiter dashboard statistics.
    All heavy DB work is done in a single call chain;
    queries are grouped and batched to minimise round-trips.
    """

    def get_dashboard(
        self,
        days: int = 30,
        *,
        qualified_min_score: float = 50.0,
        top_tier_min_score: float = 75.0,
        skill_distribution_limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Full dashboard payload for GET /api/stats/.
        `days` — trend window. Thresholds tune the candidate funnel stages.
        """
        since = timezone.now() - timedelta(days=days)

        overview = self._overview()
        pipeline = self._pipeline()
        per_job = self._per_job_stats()
        score_dist = self._score_distribution()
        skills = self._skills_gap()
        trends = self._time_trends(since, days)
        top_candidates = self._top_candidates()
        users_summary = self._users_summary()
        email_stats = self._email_stats()

        candidate_funnel = self._candidate_funnel_visual(
            qualified_min_score=qualified_min_score,
            top_tier_min_score=top_tier_min_score,
        )
        skill_distribution = self._skill_distribution_pct(limit=skill_distribution_limit)
        experience_distribution = self._experience_distribution_pct()
        salary_insights = self._salary_insights()
        location_breakdown = self._location_breakdown_pct()

        return {
            "generated_at": timezone.now().isoformat(),
            "period_days": days,
            "funnel_thresholds": {
                "qualified_min_ai_score": qualified_min_score,
                "top_tier_min_ai_score": top_tier_min_score,
            },
            "overview": overview,
            "pipeline": pipeline,
            "candidate_funnel": candidate_funnel,
            "skill_distribution": skill_distribution,
            "experience_distribution": experience_distribution,
            "salary_insights": salary_insights,
            "location_breakdown": location_breakdown,
            "per_job": per_job,
            "score_distribution": score_dist,
            "skills_gap": skills,
            "trends": trends,
            "top_candidates": top_candidates,
            "users": users_summary,
            "emails": email_stats,
        }

    # ------------------------------------------------------------------
    # 1. Overview counts
    # ------------------------------------------------------------------

    def _overview(self) -> Dict[str, Any]:
        from apps.jobs.models import Job
        from apps.candidates.models import Candidate
        from apps.ranking.models import RankingSession, CandidateRanking

        total_jobs = Job.objects.count()
        active_jobs = Job.objects.filter(is_active=True).count()
        total_candidates = Candidate.objects.count()
        active_candidates = Candidate.objects.filter(is_active=True).count()
        candidates_with_cv = Candidate.objects.filter(
            is_active=True, cv_file__isnull=False
        ).exclude(cv_file="").count()
        candidates_with_embedding = Candidate.objects.filter(
            is_active=True
        ).exclude(embedding_vector=[]).count()

        total_sessions = RankingSession.objects.count()
        total_rankings = CandidateRanking.objects.count()
        reviewed_rankings = CandidateRanking.objects.filter(
            reviewed_by__isnull=False
        ).count()

        review_rate = (
            round(reviewed_rankings / total_rankings * 100, 1)
            if total_rankings > 0
            else 0
        )

        agg = CandidateRanking.objects.aggregate(
            avg_score=Avg("ai_score"),
            max_score=Max("ai_score"),
            min_score=Min("ai_score"),
        )

        return {
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "inactive_jobs": total_jobs - active_jobs,
            "total_candidates": total_candidates,
            "active_candidates": active_candidates,
            "candidates_with_cv": candidates_with_cv,
            "candidates_with_embedding": candidates_with_embedding,
            "total_ranking_sessions": total_sessions,
            "total_rankings": total_rankings,
            "reviewed_rankings": reviewed_rankings,
            "review_rate_pct": review_rate,
            "avg_ai_score": round(agg["avg_score"] or 0, 2),
            "max_ai_score": round(agg["max_score"] or 0, 2),
            "min_ai_score": round(agg["min_score"] or 0, 2),
        }

    # ------------------------------------------------------------------
    # 2. Candidate pipeline funnel
    # ------------------------------------------------------------------

    def _pipeline(self) -> Dict[str, Any]:
        from apps.ranking.models import CandidateRanking

        counts = (
            CandidateRanking.objects.values("human_decision")
            .annotate(count=Count("id"))
        )
        funnel = {"pending": 0, "shortlisted": 0, "accepted": 0, "rejected": 0}
        for row in counts:
            key = row["human_decision"]
            if key in funnel:
                funnel[key] = row["count"]

        total = sum(funnel.values())
        funnel_pct = {}
        for k, v in funnel.items():
            funnel_pct[f"{k}_pct"] = round(v / total * 100, 1) if total else 0

        return {
            **funnel,
            **funnel_pct,
            "total": total,
            "acceptance_rate_pct": (
                round(funnel["accepted"] / (funnel["accepted"] + funnel["rejected"]) * 100, 1)
                if (funnel["accepted"] + funnel["rejected"]) > 0
                else 0
            ),
        }

    # ------------------------------------------------------------------
    # 2b. Recruiter dashboard funnel & distributions (single API)
    # ------------------------------------------------------------------

    def _active_candidates_with_cv_qs(self):
        from apps.candidates.models import Candidate

        return Candidate.objects.filter(is_active=True, cv_file__isnull=False).exclude(
            cv_file=""
        )

    def _candidate_funnel_visual(
        self,
        qualified_min_score: float,
        top_tier_min_score: float,
    ) -> Dict[str, Any]:
        """
        Pipeline-style counts for UI: total CVs → qualified (by max AI score) → top tier → interview.
        Pool = active candidates with a CV file. Interview = shortlisted | accepted on any ranking.
        """
        from apps.ranking.models import CandidateRanking

        pool_qs = self._active_candidates_with_cv_qs()
        total_cvs = pool_qs.count()
        pool_ids = set(pool_qs.values_list("id", flat=True))

        max_by_cand = {
            row["candidate_id"]: row["m"]
            for row in CandidateRanking.objects.values("candidate_id").annotate(
                m=Max("ai_score")
            )
        }
        qualified_ids = {
            cid
            for cid, m in max_by_cand.items()
            if m is not None and float(m) >= qualified_min_score
        }
        top_ids = {
            cid
            for cid, m in max_by_cand.items()
            if m is not None and float(m) >= top_tier_min_score
        }

        qualified_in_pool = len(qualified_ids & pool_ids)
        top_in_pool = len(top_ids & pool_ids)

        interview_ids = set(
            CandidateRanking.objects.filter(
                human_decision__in=["shortlisted", "accepted"]
            ).values_list("candidate_id", flat=True).distinct()
        )
        interview_in_pool = len(interview_ids & pool_ids)

        def pct(num: int, den: int) -> float:
            return round(num / den * 100, 1) if den else 0.0

        stages = [
            {
                "key": "total_cvs",
                "label": "Total CVs",
                "count": total_cvs,
                "pct_of_total": pct(total_cvs, total_cvs),
            },
            {
                "key": "qualified",
                "label": "Qualified",
                "count": qualified_in_pool,
                "pct_of_total": pct(qualified_in_pool, total_cvs),
                "definition": (
                    f"Active candidates with CV whose maximum AI score across all "
                    f"rankings is ≥ {qualified_min_score}."
                ),
            },
            {
                "key": "top_candidates",
                "label": "Top candidates",
                "count": top_in_pool,
                "pct_of_total": pct(top_in_pool, total_cvs),
                "definition": (
                    f"Active candidates with CV whose maximum AI score across all "
                    f"rankings is ≥ {top_tier_min_score}."
                ),
            },
            {
                "key": "interview_selected",
                "label": "Interview selected",
                "count": interview_in_pool,
                "pct_of_total": pct(interview_in_pool, total_cvs),
                "definition": (
                    "Distinct active candidates with CV that have at least one ranking "
                    "with human_decision shortlisted or accepted."
                ),
            },
        ]

        return {
            "base": "active_candidates_with_cv_file",
            "total_base": total_cvs,
            "stages": stages,
        }

    def _skill_distribution_pct(self, limit: int = 20) -> Dict[str, Any]:
        """
        Share of active candidates (with ≥1 extracted skill) that list each skill.
        Percentages can sum to >100% because candidates have multiple skills.
        """
        from apps.candidates.models import Candidate

        qs = Candidate.objects.filter(is_active=True)
        skill_counter: Counter = Counter()
        with_skills = 0
        for skills in qs.values_list("skills", flat=True):
            items = skills or []
            if not items:
                continue
            with_skills += 1
            seen = set()
            for raw in items:
                if not raw:
                    continue
                s = str(raw).strip()
                if not s:
                    continue
                key = s[:120]
                if key not in seen:
                    seen.add(key)
                    skill_counter[key] += 1

        denom = with_skills
        skills_out = []
        for name, cnt in skill_counter.most_common(limit):
            skills_out.append(
                {
                    "skill": name,
                    "candidate_count": cnt,
                    "pct_of_candidates_with_skills": (
                        round(cnt / denom * 100, 1) if denom else 0.0
                    ),
                }
            )

        return {
            "denominator": "active_candidates_with_at_least_one_skill",
            "candidates_with_skills_count": with_skills,
            "note": "Percentages are % of candidates who have any skill listed, not % of all candidates.",
            "skills": skills_out,
        }

    def _experience_distribution_pct(self) -> Dict[str, Any]:
        """
        Buckets by candidate.experience_years: junior 0–2, middle 3–5, senior 6+.
        """
        from apps.candidates.models import Candidate

        buckets = {"junior": 0, "middle": 0, "senior": 0, "unknown": 0}
        for ey in Candidate.objects.filter(is_active=True).values_list(
            "experience_years", flat=True
        ):
            if ey is None:
                buckets["unknown"] += 1
            elif ey <= 2:
                buckets["junior"] += 1
            elif ey <= 5:
                buckets["middle"] += 1
            else:
                buckets["senior"] += 1

        total = sum(buckets.values())
        breakdown = []
        labels = {
            "junior": "Junior (0–2 years)",
            "middle": "Middle (3–5 years)",
            "senior": "Senior (6+ years)",
            "unknown": "Unknown",
        }
        for key in ("junior", "middle", "senior", "unknown"):
            c = buckets[key]
            breakdown.append(
                {
                    "key": key,
                    "label": labels[key],
                    "count": c,
                    "pct": round(c / total * 100, 1) if total else 0.0,
                }
            )

        return {
            "denominator": "active_candidates",
            "total": total,
            "buckets": breakdown,
        }

    def _salary_insights(self) -> Dict[str, Any]:
        """
        From active jobs with both salary_min and salary_max: range and average midpoint.
        """
        from apps.jobs.models import Job
        from decimal import Decimal

        jobs = Job.objects.filter(
            is_active=True,
            salary_min__isnull=False,
            salary_max__isnull=False,
        )
        midpoints: list = []
        currencies: Counter = Counter()
        global_min: Decimal | None = None
        global_max: Decimal | None = None

        for j in jobs:
            if j.salary_min is None or j.salary_max is None:
                continue
            smin, smax = j.salary_min, j.salary_max
            mid = (smin + smax) / 2
            midpoints.append(float(mid))
            cur = (j.currency or "USD").strip() or "USD"
            currencies[cur] += 1
            if global_min is None or smin < global_min:
                global_min = smin
            if global_max is None or smax > global_max:
                global_max = smax

        if not midpoints:
            return {
                "has_data": False,
                "jobs_with_salary_count": 0,
                "currency": None,
                "salary_min": None,
                "salary_max": None,
                "avg_expected_salary": None,
                "note": "No active jobs with both salary_min and salary_max set.",
            }

        primary_currency = currencies.most_common(1)[0][0]
        return {
            "has_data": True,
            "jobs_with_salary_count": len(midpoints),
            "currency": primary_currency,
            "currencies_mix": [{"currency": c, "jobs": n} for c, n in currencies.most_common()],
            "salary_min": float(global_min) if global_min is not None else None,
            "salary_max": float(global_max) if global_max is not None else None,
            "avg_expected_salary": round(sum(midpoints) / len(midpoints), 2),
            "note": "Based on active Job rows: average of (salary_min + salary_max) / 2 per job.",
        }

    def _location_breakdown_pct(self) -> Dict[str, Any]:
        """
        By target_job.location for active candidates; 'No target job' if unassigned.
        """
        from apps.candidates.models import Candidate

        loc_counter: Counter = Counter()
        qs = Candidate.objects.filter(is_active=True).select_related("target_job")
        total = qs.count()
        for c in qs.iterator(chunk_size=500):
            if c.target_job_id and c.target_job:
                loc = (c.target_job.location or "").strip() or "Unknown"
            else:
                loc = "No target job"
            loc_counter[loc[:200]] += 1

        rows = []
        for name, cnt in loc_counter.most_common(30):
            rows.append(
                {
                    "location": name,
                    "count": cnt,
                    "pct": round(cnt / total * 100, 1) if total else 0.0,
                }
            )

        return {
            "denominator": "active_candidates",
            "total": total,
            "locations": rows,
        }

    # ------------------------------------------------------------------
    # 3. Per-job statistics
    # ------------------------------------------------------------------

    def _per_job_stats(self) -> list:
        from apps.jobs.models import Job
        from apps.candidates.models import Candidate
        from apps.ranking.models import CandidateRanking, RankingSession

        jobs = Job.objects.all().order_by("-created_at")
        result = []

        # Applicants count per job
        applicants_map = {
            row["target_job_id"]: row["cnt"]
            for row in Candidate.objects.filter(is_active=True)
            .values("target_job_id")
            .annotate(cnt=Count("id"))
        }

        for job in jobs:
            # Latest session for this job
            session = (
                RankingSession.objects.filter(job=job).order_by("-created_at").first()
            )

            job_stats: Dict[str, Any] = {
                "job_id": job.id,
                "job_title": job.title,
                "company": job.company,
                "level": job.level,
                "job_type": job.job_type,
                "is_active": job.is_active,
                "applicants_count": applicants_map.get(job.id, 0),
                "required_skills": job.required_skills,
                "min_experience": job.min_experience,
                "ranked_count": 0,
                "latest_session_id": None,
                "latest_session_date": None,
                "avg_score": None,
                "max_score": None,
                "min_score": None,
                "pending": 0,
                "shortlisted": 0,
                "accepted": 0,
                "rejected": 0,
                "email_sent_count": 0,
            }

            if session:
                rankings_qs = CandidateRanking.objects.filter(session=session)
                agg = rankings_qs.aggregate(
                    cnt=Count("id"),
                    avg=Avg("ai_score"),
                    hi=Max("ai_score"),
                    lo=Min("ai_score"),
                )
                job_stats["ranked_count"] = agg["cnt"] or 0
                job_stats["avg_score"] = round(agg["avg"] or 0, 2)
                job_stats["max_score"] = round(agg["hi"] or 0, 2)
                job_stats["min_score"] = round(agg["lo"] or 0, 2)
                job_stats["latest_session_id"] = session.id
                job_stats["latest_session_date"] = session.created_at.isoformat()

                for row in rankings_qs.values("human_decision").annotate(cnt=Count("id")):
                    key = row["human_decision"]
                    if key in job_stats:
                        job_stats[key] = row["cnt"]

                job_stats["email_sent_count"] = rankings_qs.filter(email_sent=True).count()

            result.append(job_stats)

        return result

    # ------------------------------------------------------------------
    # 4. Score distribution histogram
    # ------------------------------------------------------------------

    def _score_distribution(self) -> list:
        from apps.ranking.models import CandidateRanking

        qs = CandidateRanking.objects.all()
        buckets = [
            ("0–20", 0, 20),
            ("20–40", 20, 40),
            ("40–60", 40, 60),
            ("60–80", 60, 80),
            ("80–100", 80, 100.01),
        ]
        result = []
        for label, lo, hi in buckets:
            cnt = qs.filter(ai_score__gte=lo, ai_score__lt=hi).count()
            result.append({"range": label, "count": cnt})
        return result

    # ------------------------------------------------------------------
    # 5. Skills gap analysis
    # ------------------------------------------------------------------

    def _skills_gap(self) -> Dict[str, Any]:
        from apps.ranking.models import CandidateRanking

        # Pull all matched/missing arrays from rankings
        rankings = CandidateRanking.objects.values("matched_skills", "missing_skills")

        missing_counter: Counter = Counter()
        matched_counter: Counter = Counter()

        for r in rankings:
            for skill in (r["missing_skills"] or []):
                if skill:
                    missing_counter[skill.strip()] += 1
            for skill in (r["matched_skills"] or []):
                if skill:
                    matched_counter[skill.strip()] += 1

        return {
            "most_missing": [
                {"skill": skill, "missing_in_count": cnt}
                for skill, cnt in missing_counter.most_common(15)
            ],
            "most_matched": [
                {"skill": skill, "matched_in_count": cnt}
                for skill, cnt in matched_counter.most_common(15)
            ],
            "unique_missing_skills": len(missing_counter),
            "unique_matched_skills": len(matched_counter),
        }

    # ------------------------------------------------------------------
    # 6. Time trends
    # ------------------------------------------------------------------

    def _time_trends(self, since, days: int) -> Dict[str, Any]:
        from apps.candidates.models import Candidate
        from apps.ranking.models import RankingSession

        # Candidates uploaded per day
        cand_by_day = (
            Candidate.objects.filter(created_at__gte=since)
            .extra(select={"day": "date(created_at)"})
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        candidates_trend = [
            {"date": str(row["day"]), "count": row["count"]} for row in cand_by_day
        ]

        # Ranking sessions per day
        sessions_by_day = (
            RankingSession.objects.filter(created_at__gte=since)
            .extra(select={"day": "date(created_at)"})
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        sessions_trend = [
            {"date": str(row["day"]), "count": row["count"]} for row in sessions_by_day
        ]

        return {
            "period_days": days,
            "candidates_uploaded_per_day": candidates_trend,
            "ranking_sessions_per_day": sessions_trend,
            "candidates_last_period": sum(r["count"] for r in candidates_trend),
            "sessions_last_period": sum(r["count"] for r in sessions_trend),
        }

    # ------------------------------------------------------------------
    # 7. Top scoring candidates
    # ------------------------------------------------------------------

    def _top_candidates(self, limit: int = 10) -> list:
        from apps.ranking.models import CandidateRanking
        from apps.ranking.rank_utils import leaderboard_rank_score_100

        top = (
            CandidateRanking.objects.select_related("candidate", "session__job")
            .order_by("-ai_score")[:limit]
        )
        result = []
        for cr in top:
            cand = cr.candidate
            result.append(
                {
                    "candidate_id": cand.id,
                    "name": cand.name,
                    "email": cand.email,
                    "github": cand.github or None,
                    "skills": cand.skills,
                    "experience_years": cand.experience_years,
                    "ai_score": cr.ai_score,
                    "ai_rank": cr.ai_rank,
                    "rank": (
                        float(cr.rank)
                        if cr.rank is not None
                        else leaderboard_rank_score_100(
                            cr.ai_rank,
                            int(cr.session.candidates_count or 0) or cr.ai_rank,
                        )
                    ),
                    "rank_position": cr.ai_rank,
                    "human_decision": cr.human_decision,
                    "job_id": cr.session.job_id,
                    "job_title": cr.session.job.title,
                    "company": cr.session.job.company,
                    "email_sent": cr.email_sent,
                    "email_type": cr.email_type,
                }
            )
        return result

    # ------------------------------------------------------------------
    # 8. Users summary
    # ------------------------------------------------------------------

    def _users_summary(self) -> Dict[str, Any]:
        from django.contrib.auth import get_user_model
        from apps.candidates.models import Candidate

        User = get_user_model()
        total_recruiters = User.objects.filter(role="recruiter").count()
        total_candidates = User.objects.filter(role="candidate").count()
        cands_with_profile = Candidate.objects.filter(
            user__isnull=False, is_active=True
        ).count()
        cands_without_profile = total_candidates - cands_with_profile

        return {
            "total_users": total_recruiters + total_candidates,
            "total_recruiters": total_recruiters,
            "total_candidate_accounts": total_candidates,
            "candidate_accounts_with_cv_profile": cands_with_profile,
            "candidate_accounts_without_cv_profile": cands_without_profile,
        }

    # ------------------------------------------------------------------
    # 9. Email notification stats
    # ------------------------------------------------------------------

    def _email_stats(self) -> Dict[str, Any]:
        from apps.ranking.models import CandidateRanking

        total_sent = CandidateRanking.objects.filter(email_sent=True).count()
        accept_sent = CandidateRanking.objects.filter(
            email_sent=True, email_type="accept"
        ).count()
        reject_sent = CandidateRanking.objects.filter(
            email_sent=True, email_type="reject"
        ).count()
        pending_notification = CandidateRanking.objects.filter(
            email_sent=False,
        ).exclude(human_decision="pending").count()

        return {
            "total_emails_sent": total_sent,
            "accept_emails_sent": accept_sent,
            "reject_emails_sent": reject_sent,
            "pending_notification": pending_notification,
            "email_coverage_pct": round(
                total_sent / max(accept_sent + reject_sent + 1, 1) * 100, 1
            ),
        }
