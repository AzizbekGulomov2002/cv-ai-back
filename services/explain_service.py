"""
Explanation service for generating human-readable explanations of AI ranking decisions.
MANDATORY for high-risk AI system compliance.
"""
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from apps.candidates.models import Candidate
from apps.jobs.models import Job

logger = logging.getLogger(__name__)

# Og‘irliklar yig‘indisi 1.0 — faqat kasbiy moslik; himoyalangan belgilar skoringda ishlatilmaydi.
MATCH_DIMENSION_WEIGHTS: Dict[str, float] = {
    "semantic_alignment": 0.32,
    "required_skills": 0.28,
    "preferred_skills": 0.12,
    "experience_fit": 0.18,
    "education_signals": 0.10,
}


class ExplanationService:
    """
    Service class for generating explanations of AI ranking decisions.
    Critical for transparency and compliance with high-risk AI regulations.
    """
    
    def __init__(self):
        """Initialize the explanation service."""
        pass

    def compute_match_breakdown(
        self,
        candidate: Candidate,
        job: Job,
        semantic_score_0_100: float,
    ) -> Dict[str, Any]:
        """
        Job bilan nomzod mosligini o‘lcham-bo‘yicha (WHY bu ball) — vakant + embedding.

        semantic_score_0_100: embedding cosine dan 0–100 ga map qilingan ball.
        """
        semantic = max(0.0, min(100.0, float(semantic_score_0_100)))
        sem_expl = (
            f"Semantic similarity between job text and CV embedding text is {semantic:.1f}/100 "
            "(content overlap signal, not a hiring decision)."
        )

        matched_req, matched_pref, missing_req = self._find_skill_matches(
            candidate.skills or [],
            job.required_skills or [],
            job.preferred_skills or [],
        )
        n_req = len(job.required_skills or [])
        n_pref = len(job.preferred_skills or [])

        if n_req > 0:
            req_score = (len(matched_req) / n_req) * 100.0
            req_expl = (
                f"Required skills: {len(matched_req)}/{n_req} explicit matches "
                f"({', '.join(matched_req[:8]) or 'none'}{', …' if len(matched_req) > 8 else ''}). "
                f"Missing required: {', '.join(missing_req[:6]) or 'none'}"
                f"{' …' if len(missing_req) > 6 else ''}."
            )
        else:
            req_score = 75.0
            req_expl = "Job has no explicit required_skills list; neutral score applied."

        if n_pref > 0:
            pref_score = (len(matched_pref) / n_pref) * 100.0
            pref_expl = (
                f"Preferred skills: {len(matched_pref)}/{n_pref} matched "
                f"({', '.join(matched_pref[:6]) or 'none'})."
            )
        else:
            pref_score = 70.0
            pref_expl = "No preferred_skills on job; neutral contribution."

        cy = candidate.experience_years
        min_e = job.min_experience or 0
        if cy is None:
            exp_score = 55.0
            exp_expl = "Years of experience not stated on candidate; conservative score."
        elif min_e == 0:
            exp_score = 100.0
            exp_expl = f"Candidate reports {cy} years experience; job has no minimum bar."
        elif cy >= min_e:
            exp_score = 100.0
            exp_expl = (
                f"Experience fit: candidate {cy} y ≥ required {min_e} y."
            )
        else:
            gap = min_e - cy
            exp_score = max(0.0, 100.0 - gap * 18.0)
            exp_expl = (
                f"Experience gap: candidate {cy} y vs minimum {min_e} y "
                f"({gap} year shortfall reduces this dimension)."
            )

        edu_text = (candidate.education or "").lower()
        req_blob = f"{job.requirements} {job.description}".lower()
        edu_keywords = [
            "degree",
            "bachelor",
            "master",
            "phd",
            "university",
            "diploma",
        ]
        if edu_text.strip():
            hits = sum(1 for k in edu_keywords if k in edu_text)
            req_hits = sum(1 for k in edu_keywords if k in req_blob)
            if req_hits > 0:
                edu_score = min(100.0, 40.0 + hits * 15.0 + req_hits * 5.0)
                edu_expl = (
                    "Education section present; overlap with job education-related wording "
                    f"contributes to this sub-score (heuristic, not credential verification)."
                )
            else:
                edu_score = min(100.0, 50.0 + hits * 12.0)
                edu_expl = (
                    "Education text extracted; job text does not stress formal education heavily."
                )
        else:
            edu_score = 45.0
            edu_expl = "No education summary on candidate profile; low education signal."

        dimensions: List[Dict[str, Any]] = [
            {
                "id": "semantic_alignment",
                "label": "Semantic alignment (job ↔ CV text)",
                "score": round(semantic, 2),
                "weight": MATCH_DIMENSION_WEIGHTS["semantic_alignment"],
                "weighted_contribution": round(
                    semantic * MATCH_DIMENSION_WEIGHTS["semantic_alignment"], 2
                ),
                "explanation": sem_expl,
            },
            {
                "id": "required_skills",
                "label": "Required skills coverage",
                "score": round(req_score, 2),
                "weight": MATCH_DIMENSION_WEIGHTS["required_skills"],
                "weighted_contribution": round(
                    req_score * MATCH_DIMENSION_WEIGHTS["required_skills"], 2
                ),
                "explanation": req_expl,
                "matched": matched_req,
                "missing": missing_req,
            },
            {
                "id": "preferred_skills",
                "label": "Preferred skills",
                "score": round(pref_score, 2),
                "weight": MATCH_DIMENSION_WEIGHTS["preferred_skills"],
                "weighted_contribution": round(
                    pref_score * MATCH_DIMENSION_WEIGHTS["preferred_skills"], 2
                ),
                "explanation": pref_expl,
                "matched": matched_pref,
            },
            {
                "id": "experience_fit",
                "label": "Experience vs job minimum",
                "score": round(exp_score, 2),
                "weight": MATCH_DIMENSION_WEIGHTS["experience_fit"],
                "weighted_contribution": round(
                    exp_score * MATCH_DIMENSION_WEIGHTS["experience_fit"], 2
                ),
                "explanation": exp_expl,
            },
            {
                "id": "education_signals",
                "label": "Education signals (heuristic)",
                "score": round(edu_score, 2),
                "weight": MATCH_DIMENSION_WEIGHTS["education_signals"],
                "weighted_contribution": round(
                    edu_score * MATCH_DIMENSION_WEIGHTS["education_signals"], 2
                ),
                "explanation": edu_expl,
            },
        ]

        composite = sum(d["weighted_contribution"] for d in dimensions)
        composite = max(0.0, min(100.0, composite))

        scoring_summary = self._build_scoring_summary(dimensions, composite)

        return {
            "schema_version": 1,
            "job_id": job.id,
            "candidate_id": candidate.id,
            "composite_score": round(composite, 2),
            "dimensions": dimensions,
            "scoring_summary": scoring_summary,
            "weights": MATCH_DIMENSION_WEIGHTS,
            "human_in_the_loop_notice": (
                "This score is decision-support only. No automated hiring decision. "
                "HR must Accept / Reject / Shortlist with documented review."
            ),
            "fairness_notice": (
                "Gender, age, ethnicity, and religion are not used as model inputs for these dimensions. "
                "CV proxy flags (if any) are stored separately for transparency review."
            ),
        }

    def _build_scoring_summary(
        self, dimensions: List[Dict[str, Any]], composite: float
    ) -> Dict[str, Any]:
        """
        Dimansiyalarni kuchli/o'rtacha/kuchsiz toifalariga ajratadi.
        Har biri uchun aniq raqamlar va sabab (reason) ko'rsatiladi.

        Thresholds:
          strong  : score >= 75
          average : 50 <= score < 75
          weak    : score < 50
        """
        strong, average, weak = [], [], []

        for d in dimensions:
            score_val = float(d.get("score", 0))
            entry = {
                "id": d.get("id"),
                "label": d.get("label"),
                "score": round(score_val, 1),
                "weight_pct": round(float(d.get("weight", 0)) * 100, 0),
                "weighted_contribution": round(float(d.get("weighted_contribution", 0)), 2),
                "reason": d.get("explanation", ""),
            }
            if "matched" in d:
                entry["matched"] = d["matched"]
            if "missing" in d:
                entry["missing"] = d["missing"]

            if score_val >= 75:
                strong.append(entry)
            elif score_val >= 50:
                average.append(entry)
            else:
                weak.append(entry)

        # Overall tier
        if composite >= 75:
            overall_tier = "strong"
            overall_label = "Strong Match"
        elif composite >= 50:
            overall_tier = "average"
            overall_label = "Average Match"
        else:
            overall_tier = "weak"
            overall_label = "Weak Match"

        return {
            "composite_score": round(composite, 2),
            "overall_tier": overall_tier,
            "overall_label": overall_label,
            "strong": strong,
            "average": average,
            "weak": weak,
            "counts": {
                "strong": len(strong),
                "average": len(average),
                "weak": len(weak),
            },
            "summary_text": self._scoring_summary_text(strong, average, weak, composite),
        }

    @staticmethod
    def _scoring_summary_text(
        strong: List, average: List, weak: List, composite: float
    ) -> str:
        """Human-readable qisqa xulosa."""
        lines = [
            f"Overall composite score: {composite:.1f}/100.",
        ]
        if strong:
            names = ", ".join(e["label"] for e in strong)
            lines.append(
                f"Strong areas ({len(strong)}): {names}."
            )
        if average:
            names = ", ".join(e["label"] for e in average)
            lines.append(
                f"Average areas ({len(average)}): {names}."
            )
        if weak:
            names = ", ".join(e["label"] for e in weak)
            lines.append(
                f"Weak areas ({len(weak)}): {names}."
            )
        return " ".join(lines)

    def narrative_from_match_breakdown(self, breakdown: Dict[str, Any]) -> str:
        """match_breakdown dan inson o‘qiydigan WHY matn."""
        if not breakdown or "dimensions" not in breakdown:
            return "No structured explanation available."
        lines = [
            f"Overall match index: {breakdown.get('composite_score', 0):.1f}/100 "
            "(recommendation support — not a hire/reject decision).",
            "",
            "How this score is composed:",
        ]
        for d in breakdown.get("dimensions", []):
            pct = float(d.get("weight", 0)) * 100.0
            lines.append(
                f"• {d.get('label', d.get('id'))}: {d.get('score', 0):.0f}/100 "
                f"(weight {pct:.0f}% of total) — {d.get('explanation', '')}"
            )
        lines.append("")
        lines.append(breakdown.get("human_in_the_loop_notice", ""))
        lines.append(breakdown.get("fairness_notice", ""))
        return "\n".join(lines)

    def leaderboard_footer_for_ranking(
        self,
        *,
        position: int,
        session_total: int,
        rank_score_0_100: float,
        composite_score: float,
        session_id: int,
        job_title: str,
    ) -> str:
        """
        Qator oxiriga qo‘shiladi: DB dagi ``rank`` (0–100, o‘rindan hisoblangan) va sessiya konteksti.
        """
        return (
            "\n\n---\nLEADERBOARD_CONTEXT (audit / UI / LLM):\n"
            f"- leaderboard_rank_0_100 (DB column CandidateRanking.rank): {rank_score_0_100:.4f}/100 "
            f"(formula: 100*(N-pos+1)/N; pos={position}, N={session_total})\n"
            f"- position_in_session (1=best): {position} of {session_total}\n"
            f"- ranking_session_id: {session_id}\n"
            f"- job_title: {job_title}\n"
            f"- composite_match_score: {composite_score:.4f}/100\n"
        )

    def merge_bias_flags_for_ranking(
        self,
        heuristic_flags: List[str],
        fairness_scan: Optional[dict],
    ) -> List[str]:
        """Heuristic bias + LLM fairness_scan — tartibsiz takrorlarsiz ro‘yxat."""
        out: List[str] = list(heuristic_flags or [])
        if isinstance(fairness_scan, dict):
            if fairness_scan.get("gender_proxy_detected"):
                out.append("transparency:gender_proxy_text_in_cv")
            if fairness_scan.get("age_proxy_detected"):
                out.append("transparency:age_proxy_text_in_cv")
            for x in fairness_scan.get("other_proxy_flags") or []:
                if isinstance(x, str) and x.strip():
                    out.append(f"transparency:{x.strip()[:80]}")
        # dedupe preserve order
        seen: Set[str] = set()
        unique: List[str] = []
        for f in out:
            if f not in seen:
                seen.add(f)
                unique.append(f)
        return unique
    
    def _normalize_skills(self, skills: List[str]) -> Set[str]:
        """
        Normalize skills for comparison (lowercase, stripped).
        
        Args:
            skills: List of skills to normalize
            
        Returns:
            Set[str]: Normalized skills set
        """
        if not skills:
            return set()
        
        return {skill.lower().strip() for skill in skills if skill.strip()}
    
    def _find_skill_matches(self, candidate_skills: List[str], 
                           job_required_skills: List[str],
                           job_preferred_skills: List[str] = None) -> Tuple[List[str], List[str], List[str]]:
        """
        Find matching and missing skills between candidate and job.
        
        Args:
            candidate_skills: Skills listed in candidate's CV
            job_required_skills: Required skills for the job
            job_preferred_skills: Preferred skills for the job
            
        Returns:
            tuple: (matched_required, matched_preferred, missing_required)
        """
        if job_preferred_skills is None:
            job_preferred_skills = []
        
        # Normalize all skill sets
        candidate_set = self._normalize_skills(candidate_skills)
        required_set = self._normalize_skills(job_required_skills)
        preferred_set = self._normalize_skills(job_preferred_skills)
        
        # Find matches
        matched_required = []
        matched_preferred = []
        missing_required = []
        
        # Check required skills
        for skill in job_required_skills:
            skill_normalized = skill.lower().strip()
            if skill_normalized in candidate_set:
                matched_required.append(skill)
            else:
                missing_required.append(skill)
        
        # Check preferred skills
        for skill in job_preferred_skills:
            skill_normalized = skill.lower().strip()
            if skill_normalized in candidate_set:
                matched_preferred.append(skill)
        
        return matched_required, matched_preferred, missing_required
    
    def _generate_score_explanation(self, score: float) -> str:
        """
        Generate human-readable explanation for a score.
        
        Args:
            score: AI-generated score (0-100)
            
        Returns:
            str: Human-readable score explanation
        """
        if score >= 90:
            return "Excellent match - candidate profile strongly aligns with job requirements"
        elif score >= 80:
            return "Very good match - candidate has most required qualifications"
        elif score >= 70:
            return "Good match - candidate meets key requirements with minor gaps"
        elif score >= 60:
            return "Moderate match - candidate has relevant experience but some gaps exist"
        elif score >= 40:
            return "Partial match - candidate has some relevant skills but significant gaps"
        else:
            return "Low match - candidate profile does not align well with job requirements"
    
    def _generate_experience_analysis(self, candidate: Candidate, job: Job) -> str:
        """
        Generate explanation about experience match.
        
        Args:
            candidate: Candidate being evaluated
            job: Job requirements
            
        Returns:
            str: Experience analysis text
        """
        if candidate.experience_years is None:
            return "Experience level not specified in CV."
        
        if job.min_experience == 0:
            return f"Candidate has {candidate.experience_years} years of experience."
        
        if candidate.experience_years >= job.min_experience:
            excess = candidate.experience_years - job.min_experience
            if excess > 5:
                return f"Candidate significantly exceeds minimum experience requirement ({candidate.experience_years} vs {job.min_experience} years required)."
            else:
                return f"Candidate meets experience requirement ({candidate.experience_years} vs {job.min_experience} years required)."
        else:
            gap = job.min_experience - candidate.experience_years
            return f"Candidate has {gap} years less experience than required ({candidate.experience_years} vs {job.min_experience} years required)."
    
    def _generate_education_analysis(self, candidate: Candidate, job: Job) -> str:
        """
        Generate explanation about education match.
        
        Args:
            candidate: Candidate being evaluated
            job: Job requirements
            
        Returns:
            str: Education analysis text
        """
        if not candidate.education:
            return "No education information found in CV."
        
        # Simple keyword-based education analysis
        education_lower = candidate.education.lower()
        
        # Check for degree levels
        has_phd = any(word in education_lower for word in ['phd', 'ph.d', 'doctorate', 'doctoral'])
        has_masters = any(word in education_lower for word in ['master', 'msc', 'mba', 'ms'])
        has_bachelors = any(word in education_lower for word in ['bachelor', 'bsc', 'ba', 'bs'])
        
        if has_phd:
            return "Candidate has advanced doctoral-level education."
        elif has_masters:
            return "Candidate has master's level education."
        elif has_bachelors:
            return "Candidate has bachelor's level education."
        else:
            return "Candidate has educational background as specified in CV."
    
    def generate_explanation(self, candidate: Candidate, job: Job, score: float) -> Dict:
        """
        Generate comprehensive explanation for a ranking decision.
        
        Args:
            candidate: Candidate being ranked
            job: Job being matched against
            score: AI-generated matching score
            
        Returns:
            dict: Comprehensive explanation data
        """
        try:
            # Analyze skills matching
            matched_required, matched_preferred, missing_required = self._find_skill_matches(
                candidate.skills,
                job.required_skills,
                job.preferred_skills
            )
            
            # All matched skills for response
            all_matched = matched_required + matched_preferred
            
            # Generate detailed explanation text
            explanation_parts = []
            
            # Score overview
            explanation_parts.append(self._generate_score_explanation(score))
            
            # Skills analysis
            if all_matched:
                explanation_parts.append(f"Matched skills: {', '.join(all_matched)}")
            
            if missing_required:
                explanation_parts.append(f"Missing required skills: {', '.join(missing_required)}")
            
            if matched_preferred:
                explanation_parts.append(f"Additional preferred skills found: {', '.join(matched_preferred)}")
            
            # Experience analysis
            experience_text = self._generate_experience_analysis(candidate, job)
            explanation_parts.append(experience_text)
            
            # Education analysis
            education_text = self._generate_education_analysis(candidate, job)
            explanation_parts.append(education_text)
            
            # Compile final explanation
            full_explanation = " ".join(explanation_parts)
            
            # Generate bias flags (basic implementation)
            bias_flags = self._check_for_bias_indicators(candidate, job)
            
            explanation_data = {
                'matched_skills': all_matched,
                'missing_skills': missing_required,
                'explanation': full_explanation,
                'bias_flags': bias_flags,
                'score_category': self._get_score_category(score),
                'skills_match_ratio': len(matched_required) / len(job.required_skills) if job.required_skills else 0,
                'experience_match': candidate.experience_years >= job.min_experience if candidate.experience_years and job.min_experience else None
            }
            
            logger.info(f"Generated explanation for candidate {candidate.name} vs job {job.title}")
            return explanation_data
            
        except Exception as e:
            logger.error(f"Error generating explanation: {str(e)}")
            return {
                'matched_skills': [],
                'missing_skills': [],
                'explanation': f"Error generating explanation: {str(e)}",
                'bias_flags': [],
                'score_category': 'unknown',
                'skills_match_ratio': 0,
                'experience_match': None
            }
    
    def _check_for_bias_indicators(self, candidate: Candidate, job: Job) -> List[str]:
        """
        Check for potential bias indicators in the matching process.
        Basic implementation - can be enhanced with more sophisticated detection.
        
        Args:
            candidate: Candidate being evaluated
            job: Job requirements
            
        Returns:
            List[str]: List of potential bias indicators
        """
        bias_flags = []
        
        try:
            # Check for potential gender bias keywords in CV
            cv_text_lower = candidate.extracted_text.lower() if candidate.extracted_text else ""
            
            # Gender-related terms that might introduce bias
            gender_terms = ['male', 'female', 'man', 'woman', 'boy', 'girl', 'he', 'she', 
                          'husband', 'wife', 'mr.', 'mrs.', 'ms.']
            
            found_gender_terms = [term for term in gender_terms if term in cv_text_lower]
            if found_gender_terms:
                bias_flags.append(f"gender_indicators_present")
            
            # Check for age-related bias
            age_terms = ['age', 'years old', 'born in', 'birth']
            found_age_terms = [term for term in age_terms if term in cv_text_lower]
            if found_age_terms:
                bias_flags.append("age_indicators_present")
            
            # Check for name-based bias (very basic - just flag non-ASCII characters)
            if candidate.name and not candidate.name.isascii():
                bias_flags.append("non_ascii_name")
            
            # Check for education institution bias (prestige bias)
            if candidate.education:
                education_lower = candidate.education.lower()
                prestigious_terms = ['harvard', 'mit', 'stanford', 'oxford', 'cambridge', 'ivy league']
                if any(term in education_lower for term in prestigious_terms):
                    bias_flags.append("prestigious_education_mentioned")
            
            # Check for over-qualification bias
            if (candidate.experience_years and job.min_experience and 
                candidate.experience_years > job.min_experience * 2):
                bias_flags.append("potential_overqualification")
            
        except Exception as e:
            logger.error(f"Error checking bias indicators: {str(e)}")
            bias_flags.append("bias_check_error")
        
        return bias_flags
    
    def _get_score_category(self, score: float) -> str:
        """
        Categorize score into human-readable category.
        
        Args:
            score: Numeric score (0-100)
            
        Returns:
            str: Score category
        """
        if score >= 90:
            return "excellent"
        elif score >= 80:
            return "very_good"
        elif score >= 70:
            return "good"
        elif score >= 60:
            return "moderate"
        elif score >= 40:
            return "partial"
        else:
            return "low"
    
    def generate_batch_explanations(self, candidate_job_scores: List[Tuple[Candidate, Job, float]]) -> List[Dict]:
        """
        Generate explanations for multiple candidate-job pairs efficiently.
        
        Args:
            candidate_job_scores: List of (candidate, job, score) tuples
            
        Returns:
            List[Dict]: List of explanation dictionaries
        """
        explanations = []
        
        for candidate, job, score in candidate_job_scores:
            explanation = self.generate_explanation(candidate, job, score)
            explanations.append(explanation)
        
        return explanations
    
    def generate_comparative_explanation(self, rankings: List, job: Job) -> Dict:
        """
        Generate explanation comparing multiple candidates for a job.
        
        Args:
            rankings: List of CandidateRanking objects
            job: Job being filled
            
        Returns:
            dict: Comparative analysis
        """
        try:
            if not rankings:
                return {"error": "No rankings provided"}
            
            # Analyze top performers
            top_3 = rankings[:3] if len(rankings) >= 3 else rankings
            
            comparison = {
                'job_title': job.title,
                'total_candidates': len(rankings),
                'top_candidates_analysis': [],
                'skills_analysis': self._analyze_skills_across_candidates(rankings, job),
                'score_distribution': self._analyze_score_distribution(rankings)
            }
            
            for i, ranking in enumerate(top_3, 1):
                candidate_analysis = {
                    'rank': i,
                    'candidate_name': ranking.candidate.name,
                    'score': ranking.ai_score,
                    'key_strengths': ranking.matched_skills[:5],  # Top 5 matched skills
                    'main_gaps': ranking.missing_skills[:3]  # Top 3 missing skills
                }
                comparison['top_candidates_analysis'].append(candidate_analysis)
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error generating comparative explanation: {str(e)}")
            return {"error": str(e)}
    
    def _analyze_skills_across_candidates(self, rankings: List, job: Job) -> Dict:
        """Analyze skills distribution across all candidates."""
        all_matched_skills = []
        all_missing_skills = []
        
        for ranking in rankings:
            all_matched_skills.extend(ranking.matched_skills)
            all_missing_skills.extend(ranking.missing_skills)
        
        # Count frequency
        from collections import Counter
        matched_freq = Counter(all_matched_skills)
        missing_freq = Counter(all_missing_skills)
        
        return {
            'most_common_matched': matched_freq.most_common(5),
            'most_common_missing': missing_freq.most_common(5),
            'required_skills_coverage': len(matched_freq) / len(job.required_skills) if job.required_skills else 0
        }
    
    def _analyze_score_distribution(self, rankings: List) -> Dict:
        """Analyze score distribution across candidates."""
        scores = [r.ai_score for r in rankings]
        
        if not scores:
            return {}
        
        return {
            'highest_score': max(scores),
            'lowest_score': min(scores),
            'average_score': sum(scores) / len(scores),
            'score_range': max(scores) - min(scores),
            'candidates_above_70': len([s for s in scores if s >= 70])
        }