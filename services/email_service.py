"""
Email notification service for CV AI System.
Sends accept/reject emails to candidates via SMTP.
"""
import logging
from typing import List, Optional

from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.utils import timezone
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailService:
    """
    SMTP-based email notification service.
    Configure via .env: EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD.
    """

    def __init__(self):
        self.from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@cv-ai.local")
        self.frontend_url = getattr(settings, "FRONTEND_URL", "").rstrip("/")

    # ------------------------------------------------------------------
    # Accept email
    # ------------------------------------------------------------------

    def send_accept_email(
        self,
        candidate_email: str,
        candidate_name: str,
        job_title: str,
        company_name: str,
        recruiter_name: str,
        ai_score: float,
        matched_skills: List[str],
        scoring_summary: Optional[dict] = None,
        extra_message: str = "",
    ) -> bool:
        """
        Send a personalised acceptance email to a candidate.

        Returns True on success, False on failure.
        """
        subject = f"Congratulations! Your application for {job_title} at {company_name} — Next Steps"

        strong_text = ""
        if scoring_summary and scoring_summary.get("strong"):
            strong_items = [
                f"• {s['label']}: {s['score']:.0f}/100 — {s['reason']}"
                for s in scoring_summary["strong"]
            ]
            strong_text = "\n".join(strong_items)

        skills_text = ", ".join(matched_skills[:10]) if matched_skills else "Strong overall profile"

        html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; color: #333;">
  <div style="background: linear-gradient(135deg, #1a73e8, #0d47a1); padding: 24px; border-radius: 8px 8px 0 0;">
    <h1 style="color: white; margin: 0; font-size: 22px;">🎉 Congratulations, {candidate_name}!</h1>
  </div>
  <div style="background: #f9f9f9; border: 1px solid #e0e0e0; border-top: none; padding: 28px; border-radius: 0 0 8px 8px;">
    <p>We are pleased to inform you that your application for the position of <strong>{job_title}</strong>
    at <strong>{company_name}</strong> has been <span style="color:#1a73e8; font-weight:bold;">accepted</span>.</p>

    <div style="background:#e8f5e9; border-left: 4px solid #43a047; padding: 14px; border-radius: 4px; margin: 18px 0;">
      <p style="margin: 0 0 6px 0;"><strong>Your AI Match Score:</strong>
        <span style="font-size: 20px; color: #43a047; font-weight: bold;">{ai_score:.1f}/100</span>
      </p>
      <p style="margin: 0; color: #555; font-size: 13px;">
        Your profile demonstrated strong alignment with our requirements.
      </p>
    </div>

    <h3 style="color: #1a73e8; border-bottom: 1px solid #e0e0e0; padding-bottom: 8px;">
      Key Strengths We Identified
    </h3>
    <p style="background: #fff; border: 1px solid #e0e0e0; padding: 12px; border-radius: 4px; font-size: 14px;">
      <strong>Matching Skills:</strong> {skills_text}
    </p>
    {f'''<div style="background: #fff; border: 1px solid #e0e0e0; padding: 12px; border-radius: 4px; margin-top: 8px; font-size: 13px; white-space: pre-line;">{strong_text}</div>''' if strong_text else ''}

    {f'<p style="background: #fff3e0; border-left: 4px solid #ff9800; padding: 12px; border-radius: 4px; margin: 18px 0;">{extra_message}</p>' if extra_message else ''}

    <h3 style="color: #1a73e8; border-bottom: 1px solid #e0e0e0; padding-bottom: 8px;">Next Steps</h3>
    <ol style="padding-left: 20px; line-height: 1.8;">
      <li>Our recruitment team will contact you within <strong>3–5 business days</strong>.</li>
      <li>Please prepare to discuss your experience and skills further.</li>
      <li>Ensure your contact information is up to date.</li>
    </ol>

    <p style="margin-top: 24px;">Best regards,<br>
    <strong>{recruiter_name}</strong><br>
    Recruitment Team, {company_name}</p>

    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">
    <p style="font-size: 11px; color: #999;">
      This is an automated message from the AI CV Analysis System.
      AI scores are decision-support tools only and are reviewed by HR professionals.
    </p>
  </div>
</body>
</html>
"""
        text_body = strip_tags(html_body)

        return self._send(
            to_email=candidate_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )

    # ------------------------------------------------------------------
    # Reject email
    # ------------------------------------------------------------------

    def send_reject_email(
        self,
        candidate_email: str,
        candidate_name: str,
        job_title: str,
        company_name: str,
        recruiter_name: str,
        ai_score: float,
        rejection_reasons: List[dict],
        scoring_summary: Optional[dict] = None,
        extra_message: str = "",
    ) -> bool:
        """
        Send a transparent rejection email with specific reasons.

        rejection_reasons: list of dicts with keys:
          - dimension (str): which area
          - score (float): the actual score
          - reason (str): human-readable explanation
          - missing (list[str]): missing skills if applicable
        """
        subject = f"Your application for {job_title} at {company_name} — Application Update"

        # Build reasons HTML
        reasons_html_parts = []
        for r in rejection_reasons:
            dim = r.get("dimension", r.get("label", "Area"))
            score_val = r.get("score", 0)
            reason_text = r.get("reason", "")
            missing = r.get("missing", [])

            missing_html = ""
            if missing:
                missing_items = "".join(f"<li>{m}</li>" for m in missing[:8])
                missing_html = f"<ul style='margin: 4px 0 0 16px; font-size: 12px; color: #666;'>{missing_items}</ul>"

            reasons_html_parts.append(f"""
        <div style="background: #fff; border: 1px solid #e0e0e0; border-left: 3px solid #ef5350;
                    padding: 12px; border-radius: 4px; margin-bottom: 10px;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <strong style="font-size: 14px;">{dim}</strong>
            <span style="color: #ef5350; font-weight: bold; font-size: 13px;">{score_val:.0f}/100</span>
          </div>
          <p style="margin: 6px 0 0 0; font-size: 13px; color: #555;">{reason_text}</p>
          {missing_html}
        </div>""")

        reasons_block = "\n".join(reasons_html_parts) if reasons_html_parts else (
            "<p style='color:#555;'>Specific scores did not meet our current requirements.</p>"
        )

        # Weak areas from scoring_summary (additional detail for recruiter transparency)
        weak_text = ""
        if scoring_summary and scoring_summary.get("weak"):
            weak_items = [
                f"• {w['label']}: {w['score']:.0f}/100 — {w['reason']}"
                for w in scoring_summary["weak"]
            ]
            weak_text = "\n".join(weak_items)

        html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; color: #333;">
  <div style="background: linear-gradient(135deg, #546e7a, #37474f); padding: 24px; border-radius: 8px 8px 0 0;">
    <h1 style="color: white; margin: 0; font-size: 22px;">Application Update</h1>
  </div>
  <div style="background: #f9f9f9; border: 1px solid #e0e0e0; border-top: none; padding: 28px; border-radius: 0 0 8px 8px;">
    <p>Dear <strong>{candidate_name}</strong>,</p>
    <p>Thank you for applying for the position of <strong>{job_title}</strong> at <strong>{company_name}</strong>.
    After a thorough review of your application, we regret to inform you that we will not be moving forward
    at this time.</p>

    <div style="background: #fbe9e7; border-left: 4px solid #ef5350; padding: 14px; border-radius: 4px; margin: 18px 0;">
      <p style="margin: 0; font-size: 13px;">
        <strong>Your match score for this role: {ai_score:.1f}/100</strong><br>
        <span style="color: #777;">Our current threshold for this position was not met in the following areas.</span>
      </p>
    </div>

    <h3 style="color: #546e7a; border-bottom: 1px solid #e0e0e0; padding-bottom: 8px;">
      Areas That Did Not Meet Requirements
    </h3>
    {reasons_block}

    {f'<div style="background:#fff3e0; border-left: 4px solid #ff9800; padding: 12px; border-radius: 4px; margin: 18px 0; font-size: 14px;">{extra_message}</div>' if extra_message else ''}

    {f'<div style="background:#f3f4f6; border-left: 3px solid #9e9e9e; padding: 12px; border-radius: 4px; margin: 18px 0;"><strong style="font-size:13px;">Additional detail:</strong><pre style="font-size:12px; color:#555; white-space:pre-wrap; margin:6px 0 0 0;">{weak_text}</pre></div>' if weak_text else ''}

    <h3 style="color: #546e7a; border-bottom: 1px solid #e0e0e0; padding-bottom: 8px;">
      Suggestions for Future Applications
    </h3>
    <ul style="padding-left: 20px; line-height: 1.8; font-size: 14px;">
      <li>Focus on developing skills in the areas listed above.</li>
      <li>Consider adding relevant certifications or projects to your profile.</li>
      <li>We encourage you to apply for future openings that match your profile.</li>
    </ul>

    <p style="margin-top: 24px; font-size: 14px;">
      We appreciate your time and interest in joining our team. We wish you the very best in your
      job search and future endeavors.
    </p>

    <p>Sincerely,<br>
    <strong>{recruiter_name}</strong><br>
    Recruitment Team, {company_name}</p>

    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">
    <p style="font-size: 11px; color: #999;">
      This decision was made with the support of an AI CV Analysis System and reviewed by a human recruiter.
      AI-generated scores are for decision-support only and are not the sole basis for any hiring decision.
    </p>
  </div>
</body>
</html>
"""
        text_body = strip_tags(html_body)

        return self._send(
            to_email=candidate_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    def _send(
        self,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str,
    ) -> bool:
        """Send an HTML email, returns True on success."""
        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=self.from_email,
                to=[to_email],
            )
            msg.attach_alternative(html_body, "text/html")
            msg.send(fail_silently=False)
            logger.info("Email sent to %s — subject: %s", to_email, subject)
            return True
        except Exception as e:
            logger.error(
                "Failed to send email to %s — %s: %s",
                to_email,
                type(e).__name__,
                e,
            )
            return False
