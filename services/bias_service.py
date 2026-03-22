"""
Bias detection service for identifying potential discrimination in AI ranking decisions.
MANDATORY for high-risk AI system compliance.
"""
import logging
import re
from typing import Dict, List, Tuple, Optional
from collections import Counter, defaultdict
from statistics import mean, stdev

from apps.candidates.models import Candidate
from apps.jobs.models import Job
from apps.ranking.models import CandidateRanking, RankingSession

logger = logging.getLogger(__name__)


class BiasDetectionService:
    """
    Service class for detecting potential bias in AI ranking decisions.
    Essential for compliance with high-risk AI regulations.
    """
    
    # Bias detection keywords and patterns
    PROTECTED_CHARACTERISTICS = {
        'gender': {
            'keywords': ['male', 'female', 'man', 'woman', 'boy', 'girl', 'gentleman', 'lady'],
            'pronouns': ['he', 'she', 'his', 'her', 'him'],
            'titles': ['mr.', 'mrs.', 'ms.', 'miss', 'sir', 'madam']
        },
        'age': {
            'keywords': ['age', 'years old', 'born', 'birthday', 'young', 'old', 'senior', 'junior'],
            'patterns': [r'\b\d{1,2}\s*years?\s*old\b', r'\bborn\s*in\s*\d{4}\b']
        },
        'ethnicity': {
            'keywords': ['race', 'ethnic', 'nationality', 'native', 'immigrant', 'foreign'],
            'names_indicators': True  # Flag for non-ASCII names
        },
        'religion': {
            'keywords': ['christian', 'muslim', 'jewish', 'hindu', 'buddhist', 'sikh', 'church', 'mosque', 'temple']
        },
        'family_status': {
            'keywords': ['married', 'single', 'divorced', 'widow', 'husband', 'wife', 'children', 'kids', 'family']
        }
    }
    
    def __init__(self):
        """Initialize the bias detection service."""
        pass
    
    def detect_cv_bias_indicators(self, candidate: Candidate) -> Dict[str, List[str]]:
        """
        Detect potential bias indicators in a candidate's CV.
        
        Args:
            candidate: Candidate to analyze
            
        Returns:
            dict: Detected bias indicators by category
        """
        bias_indicators = defaultdict(list)
        
        if not candidate.extracted_text:
            return dict(bias_indicators)
        
        text = candidate.extracted_text.lower()
        name = candidate.name.lower() if candidate.name else ""
        
        try:
            # Check each protected characteristic
            for category, patterns in self.PROTECTED_CHARACTERISTICS.items():
                
                # Check keywords
                if 'keywords' in patterns:
                    for keyword in patterns['keywords']:
                        if keyword in text or keyword in name:
                            bias_indicators[category].append(f"keyword: {keyword}")
                
                # Check pronouns
                if 'pronouns' in patterns:
                    for pronoun in patterns['pronouns']:
                        if f" {pronoun} " in f" {text} " or f" {pronoun} " in f" {name} ":
                            bias_indicators[category].append(f"pronoun: {pronoun}")
                
                # Check titles
                if 'titles' in patterns:
                    for title in patterns['titles']:
                        if title in text or title in name:
                            bias_indicators[category].append(f"title: {title}")
                
                # Check regex patterns
                if 'patterns' in patterns:
                    for pattern in patterns['patterns']:
                        matches = re.findall(pattern, text)
                        if matches:
                            bias_indicators[category].extend([f"pattern_match: {match}" for match in matches])
                
                # Check name indicators for ethnicity
                if category == 'ethnicity' and patterns.get('names_indicators'):
                    if candidate.name and not candidate.name.isascii():
                        bias_indicators[category].append("non_ascii_name")
            
            # Additional bias checks
            self._check_education_bias(candidate, bias_indicators)
            self._check_location_bias(candidate, bias_indicators)
            
        except Exception as e:
            logger.error(f"Error detecting CV bias indicators: {str(e)}")
            bias_indicators['error'].append(str(e))
        
        return dict(bias_indicators)
    
    def _check_education_bias(self, candidate: Candidate, bias_indicators: Dict):
        """Check for education-related bias indicators."""
        if not candidate.education:
            return
        
        education_lower = candidate.education.lower()
        
        # Elite institution bias
        elite_institutions = [
            'harvard', 'yale', 'princeton', 'stanford', 'mit', 'caltech',
            'oxford', 'cambridge', 'imperial', 'lse', 'sorbonne'
        ]
        
        for institution in elite_institutions:
            if institution in education_lower:
                bias_indicators['education_privilege'].append(f"elite_institution: {institution}")
        
        # Private vs public education indicators
        private_indicators = ['private', 'prep school', 'boarding school']
        for indicator in private_indicators:
            if indicator in education_lower:
                bias_indicators['education_privilege'].append(f"private_education: {indicator}")
    
    def _check_location_bias(self, candidate: Candidate, bias_indicators: Dict):
        """Check for location-related bias indicators."""
        text = candidate.extracted_text.lower() if candidate.extracted_text else ""
        
        # Expensive area indicators (basic example - should be customized per region)
        expensive_areas = [
            'manhattan', 'beverly hills', 'silicon valley', 'monaco', 'mayfair', 
            'chelsea', 'tribeca', 'soho'
        ]
        
        for area in expensive_areas:
            if area in text:
                bias_indicators['socioeconomic'].append(f"expensive_area: {area}")
    
    def analyze_ranking_bias(self, ranking_session: RankingSession) -> Dict:
        """
        Analyze a ranking session for potential bias patterns.
        
        Args:
            ranking_session: Ranking session to analyze
            
        Returns:
            dict: Bias analysis results
        """
        rankings = CandidateRanking.objects.filter(session=ranking_session).order_by('ai_rank')
        
        if not rankings.exists():
            return {"error": "No rankings found for session"}
        
        try:
            bias_analysis = {
                'session_id': ranking_session.id,
                'job_title': ranking_session.job.title,
                'total_candidates': rankings.count(),
                'bias_flags_distribution': self._analyze_bias_flags_distribution(rankings),
                'score_bias_analysis': self._analyze_score_bias_patterns(rankings),
                'demographic_representation': self._analyze_demographic_patterns(rankings),
                'recommendations': []
            }
            
            # Generate recommendations based on findings
            bias_analysis['recommendations'] = self._generate_bias_recommendations(bias_analysis)
            
            return bias_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing ranking bias: {str(e)}")
            return {"error": str(e)}
    
    def _analyze_bias_flags_distribution(self, rankings) -> Dict:
        """Analyze distribution of bias flags across rankings."""
        all_flags = []
        flagged_candidates = 0
        
        for ranking in rankings:
            if ranking.bias_flags:
                all_flags.extend(ranking.bias_flags)
                flagged_candidates += 1
        
        flag_counts = Counter(all_flags)
        
        return {
            'total_flags': len(all_flags),
            'flagged_candidates': flagged_candidates,
            'flag_types': dict(flag_counts),
            'flagged_percentage': (flagged_candidates / rankings.count()) * 100 if rankings.count() > 0 else 0
        }
    
    def _analyze_score_bias_patterns(self, rankings) -> Dict:
        """Analyze score patterns for potential bias."""
        # Group rankings by presence of bias flags
        flagged_scores = []
        unflagged_scores = []
        
        for ranking in rankings:
            if ranking.bias_flags:
                flagged_scores.append(ranking.ai_score)
            else:
                unflagged_scores.append(ranking.ai_score)
        
        analysis = {}
        
        if flagged_scores and unflagged_scores:
            analysis['flagged_avg_score'] = mean(flagged_scores)
            analysis['unflagged_avg_score'] = mean(unflagged_scores)
            analysis['score_difference'] = analysis['unflagged_avg_score'] - analysis['flagged_avg_score']
            
            # Statistical significance test (basic)
            if len(flagged_scores) > 1 and len(unflagged_scores) > 1:
                try:
                    flagged_std = stdev(flagged_scores)
                    unflagged_std = stdev(unflagged_scores)
                    analysis['flagged_score_std'] = flagged_std
                    analysis['unflagged_score_std'] = unflagged_std
                except:
                    pass
        
        return analysis
    
    def _analyze_demographic_patterns(self, rankings) -> Dict:
        """Analyze demographic patterns in ranking positions."""
        # This is a simplified analysis - in production, you'd want more sophisticated demographic inference
        
        top_10_percent = int(rankings.count() * 0.1) or 1
        top_rankings = rankings[:top_10_percent]
        
        demographic_analysis = {
            'top_10_percent_count': top_10_percent,
            'bias_flags_in_top': sum(1 for r in top_rankings if r.bias_flags),
            'common_flags_in_top': []
        }
        
        # Analyze common bias flags in top performers
        top_flags = []
        for ranking in top_rankings:
            if ranking.bias_flags:
                top_flags.extend(ranking.bias_flags)
        
        if top_flags:
            demographic_analysis['common_flags_in_top'] = Counter(top_flags).most_common(5)
        
        return demographic_analysis
    
    def _generate_bias_recommendations(self, bias_analysis: Dict) -> List[str]:
        """Generate recommendations based on bias analysis."""
        recommendations = []
        
        flags_dist = bias_analysis.get('bias_flags_distribution', {})
        score_analysis = bias_analysis.get('score_bias_analysis', {})
        demo_analysis = bias_analysis.get('demographic_representation', {})
        
        # Check flagged percentage
        flagged_pct = flags_dist.get('flagged_percentage', 0)
        if flagged_pct > 50:
            recommendations.append("High percentage of candidates flagged for bias indicators. Review CV parsing and job requirements.")
        
        # Check score differences
        score_diff = score_analysis.get('score_difference', 0)
        if score_diff > 10:  # Significant score difference
            recommendations.append(f"Candidates with bias indicators scored {score_diff:.1f} points lower on average. Investigate potential systematic bias.")
        elif score_diff < -10:
            recommendations.append(f"Candidates with bias indicators scored {abs(score_diff):.1f} points higher on average. Review scoring logic.")
        
        # Check top performer patterns
        top_bias_flags = demo_analysis.get('bias_flags_in_top', 0)
        if top_bias_flags == 0 and demo_analysis.get('top_10_percent_count', 0) > 3:
            recommendations.append("No bias indicators found in top performers. This could indicate potential exclusion bias.")
        
        # General recommendations
        if not recommendations:
            recommendations.append("No significant bias patterns detected. Continue regular monitoring.")
        
        recommendations.append("Regularly review and update bias detection keywords and patterns.")
        recommendations.append("Ensure human oversight of all high-stakes ranking decisions.")
        
        return recommendations
    
    def generate_bias_report(self, job: Job = None, days: int = 30) -> Dict:
        """
        Generate comprehensive bias report for a period.
        
        Args:
            job: Optional specific job to analyze
            days: Number of days to analyze
            
        Returns:
            dict: Comprehensive bias report
        """
        from django.utils import timezone
        from datetime import timedelta
        
        try:
            # Get ranking sessions for the period
            start_date = timezone.now() - timedelta(days=days)
            sessions_qs = RankingSession.objects.filter(created_at__gte=start_date)
            
            if job:
                sessions_qs = sessions_qs.filter(job=job)
            
            sessions = sessions_qs.order_by('-created_at')
            
            report = {
                'report_period': f"Last {days} days",
                'job_filter': job.title if job else "All Jobs",
                'total_sessions': sessions.count(),
                'sessions_analyzed': [],
                'aggregate_statistics': {
                    'total_candidates_ranked': 0,
                    'total_bias_flags': 0,
                    'most_common_bias_types': [],
                    'average_flagged_percentage': 0
                },
                'recommendations': [],
                'generated_at': timezone.now().isoformat()
            }
            
            # Analyze each session
            flagged_percentages = []
            all_bias_types = []
            
            for session in sessions:
                session_analysis = self.analyze_ranking_bias(session)
                
                if 'error' not in session_analysis:
                    report['sessions_analyzed'].append({
                        'session_id': session.id,
                        'job_title': session.job.title,
                        'date': session.created_at.isoformat(),
                        'candidates_count': session_analysis['total_candidates'],
                        'flagged_percentage': session_analysis['bias_flags_distribution']['flagged_percentage']
                    })
                    
                    # Aggregate statistics
                    report['aggregate_statistics']['total_candidates_ranked'] += session_analysis['total_candidates']
                    report['aggregate_statistics']['total_bias_flags'] += session_analysis['bias_flags_distribution']['total_flags']
                    
                    flagged_percentages.append(session_analysis['bias_flags_distribution']['flagged_percentage'])
                    all_bias_types.extend(session_analysis['bias_flags_distribution']['flag_types'].keys())
            
            # Calculate aggregate statistics
            if flagged_percentages:
                report['aggregate_statistics']['average_flagged_percentage'] = mean(flagged_percentages)
            
            if all_bias_types:
                bias_type_counts = Counter(all_bias_types)
                report['aggregate_statistics']['most_common_bias_types'] = bias_type_counts.most_common(5)
            
            # Generate high-level recommendations
            avg_flagged = report['aggregate_statistics']['average_flagged_percentage']
            if avg_flagged > 40:
                report['recommendations'].append("High average bias flag rate detected across multiple sessions. Comprehensive review recommended.")
            elif avg_flagged > 20:
                report['recommendations'].append("Moderate bias flag rate detected. Monitor closely and consider process improvements.")
            else:
                report['recommendations'].append("Bias flag rates within acceptable range. Continue monitoring.")
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating bias report: {str(e)}")
            return {"error": str(e)}
    
    def check_job_description_bias(self, job: Job) -> Dict[str, List[str]]:
        """
        Check job description for potential bias indicators.
        
        Args:
            job: Job to analyze
            
        Returns:
            dict: Potential bias indicators in job description
        """
        bias_indicators = defaultdict(list)
        
        try:
            # Combine all job text
            job_text = f"{job.title} {job.description} {job.requirements}".lower()
            
            # Check for coded language that might exclude certain groups
            exclusionary_terms = {
                'age_bias': ['young', 'energetic', 'digital native', 'recent graduate', 'fresh'],
                'gender_bias': ['rockstar', 'ninja', 'guru', 'dominant', 'aggressive'],
                'cultural_bias': ['native speaker', 'cultural fit', 'team player'],
                'education_bias': ['top-tier university', 'ivy league', 'elite institution']
            }
            
            for bias_type, terms in exclusionary_terms.items():
                for term in terms:
                    if term in job_text:
                        bias_indicators[bias_type].append(term)
            
            # Check for unnecessarily restrictive requirements
            if 'requirements' in job.requirements.lower() and len(job.required_skills) > 15:
                bias_indicators['over_specification'].append("excessive_skill_requirements")
            
            # Check for degree requirements that might not be necessary
            degree_terms = ['degree required', 'bachelor', 'master', 'phd']
            for term in degree_terms:
                if term in job_text and job.level in ['junior', 'entry']:
                    bias_indicators['unnecessary_barriers'].append(f"degree_requirement_for_{job.level}")
            
        except Exception as e:
            logger.error(f"Error checking job description bias: {str(e)}")
            bias_indicators['error'].append(str(e))
        
        return dict(bias_indicators)
    
    def monitor_system_bias(self) -> Dict:
        """
        Perform system-wide bias monitoring.
        
        Returns:
            dict: System-wide bias monitoring results
        """
        try:
            from django.db.models import Avg, Count
            
            # Get recent data
            recent_rankings = CandidateRanking.objects.select_related(
                'candidate', 'session__job'
            ).order_by('-created_at')[:1000]  # Last 1000 rankings
            
            monitoring_report = {
                'sample_size': len(recent_rankings),
                'bias_flag_statistics': {},
                'score_distribution_by_bias': {},
                'human_override_patterns': {},
                'system_recommendations': []
            }
            
            # Analyze bias flags
            total_with_flags = sum(1 for r in recent_rankings if r.bias_flags)
            monitoring_report['bias_flag_statistics'] = {
                'total_flagged': total_with_flags,
                'percentage_flagged': (total_with_flags / len(recent_rankings)) * 100 if recent_rankings else 0
            }
            
            # Analyze human overrides vs AI decisions
            overridden_rankings = [r for r in recent_rankings if r.is_reviewed]
            if overridden_rankings:
                override_patterns = {}
                for ranking in overridden_rankings:
                    has_bias = bool(ranking.bias_flags)
                    decision = ranking.human_decision
                    
                    key = f"bias_{has_bias}_{decision}"
                    override_patterns[key] = override_patterns.get(key, 0) + 1
                
                monitoring_report['human_override_patterns'] = override_patterns
            
            # Generate system-wide recommendations
            flag_rate = monitoring_report['bias_flag_statistics']['percentage_flagged']
            
            if flag_rate > 30:
                monitoring_report['system_recommendations'].append("HIGH: Bias flag rate exceeds 30%. Immediate review of bias detection and ranking algorithms required.")
            elif flag_rate > 15:
                monitoring_report['system_recommendations'].append("MEDIUM: Elevated bias flag rate. Schedule comprehensive bias audit.")
            else:
                monitoring_report['system_recommendations'].append("LOW: Bias flag rate within normal range. Continue regular monitoring.")
            
            return monitoring_report
            
        except Exception as e:
            logger.error(f"Error in system bias monitoring: {str(e)}")
            return {"error": str(e)}