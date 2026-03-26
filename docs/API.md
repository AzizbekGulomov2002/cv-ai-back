# AI CV System — Full API Documentation

Base URL: `http://localhost:8000`  
All endpoints: `Content-Type: application/json` unless file upload (multipart).  
Auth header: `Authorization: Token <token>`

---

## 1. Authentication (`/api/auth/`)

### Roles
| Role | Access |
|---|---|
| `recruiter` | Full system access — ranking, accept/reject, all candidates |
| `candidate` | Upload own CV, view own profile, view own ranking history |

---

### `POST /api/auth/register/`
Register a new user. Open (no auth required).

**Request body:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123",
  "password_confirm": "SecurePass123",
  "role": "recruiter",          // "recruiter" | "candidate"
  "first_name": "John",
  "last_name": "Doe",
  "company": "Acme Corp",       // recruiters
  "phone": "+1234567890",
  "github": "https://github.com/jdoe",  // candidates
  "image": <file>               // optional profile photo
}
```

**Response 201:**
```json
{
  "message": "User registered successfully",
  "user": { "id": 1, "username": "john_doe", "email": "john@example.com", "role": "recruiter" },
  "token": "abc123token..."
}
```

---

### `POST /api/auth/login/`
Login with username and password. Open.

**Request:**
```json
{ "username": "john_doe", "password": "SecurePass123" }
```

**Response 200:**
```json
{
  "message": "Login successful",
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "role": "recruiter",
    "company": "Acme Corp"
  },
  "token": "abc123token..."
}
```

---

### `POST /api/auth/logout/`
Logout (invalidates token). Auth required.

---

### `GET /api/auth/profile/`
Get current user profile. Auth required.

**Response:**
```json
{
  "id": 1,
  "username": "jane_smith",
  "email": "jane@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "role": "candidate",
  "company": "",
  "phone": "",
  "image": "/media/user_images/1/profile.jpg",
  "github": "https://github.com/janesmith",
  "date_joined": "2026-03-26T10:00:00Z",
  "last_login": "2026-03-26T12:00:00Z"
}
```

---

### `PUT/PATCH /api/auth/profile/update/`
Update current user profile. Auth required.

**Fields:** `email`, `first_name`, `last_name`, `company`, `phone`, `image`, `github`

---

## 2. Candidates (`/api/candidates/`)

### Access Control
| Action | Recruiter | Candidate |
|---|---|---|
| Upload CV | ✅ (for any) | ✅ (own profile only, 1 per account) |
| List candidates | ✅ All | ✅ Own only |
| View detail | ✅ Any | ✅ Own only |
| Update | ✅ Any | ✅ Own only |
| Delete/deactivate | ✅ | ❌ |

---

### `POST /api/candidates/upload/`
Upload a CV file. **Auth required.**

- **Candidate role**: `first_name`, `last_name`, `email`, `github` auto-filled from user account.  
  Only 1 active profile allowed per candidate account.
- **Recruiter role**: uploads on behalf of candidate; fills info manually.

**Multipart form fields:**
| Field | Required | Description |
|---|---|---|
| `cv_file` | ✅ | PDF or DOCX, max 10MB |
| `job_id` | Optional | Link to a job for instant scoring |
| `name` | Optional | Overrides user account name |
| `email` | Optional | Overrides user account email |
| `phone` | Optional | Phone number |
| `github` | Optional | GitHub profile URL |

**Response 201 — with job_id (full scoring):**
```json
{
  "message": "CV processed successfully (file pipeline)",
  "candidate": { "id": 5, "name": "Jane Smith", "email": "jane@example.com", "github": "https://github.com/janesmith", ... },
  "score": 74.5,
  "ranking": {
    "score": 74.5,
    "rank_label": "Average Match",
    "tier": "average"
  },
  "matching": {
    "matched_skills": ["Python", "Django"],
    "missing_skills": ["React", "Docker"]
  },
  "explanation": "Overall match index: 74.5/100...",
  "scoring_summary": {
    "composite_score": 74.5,
    "overall_tier": "average",
    "overall_label": "Average Match",
    "strong": [
      {
        "id": "experience_fit",
        "label": "Experience vs job minimum",
        "score": 100.0,
        "weight_pct": 18.0,
        "weighted_contribution": 18.0,
        "reason": "Experience fit: candidate 5 y ≥ required 3 y."
      }
    ],
    "average": [
      {
        "id": "required_skills",
        "label": "Required skills coverage",
        "score": 66.7,
        "weight_pct": 28.0,
        "weighted_contribution": 18.68,
        "reason": "Required skills: 2/3 explicit matches (Python, Django). Missing required: React …",
        "matched": ["Python", "Django"],
        "missing": ["React"]
      }
    ],
    "weak": [
      {
        "id": "preferred_skills",
        "label": "Preferred skills",
        "score": 0.0,
        "weight_pct": 12.0,
        "weighted_contribution": 0.0,
        "reason": "Preferred skills: 0/2 matched (none)."
      }
    ],
    "counts": { "strong": 1, "average": 3, "weak": 1 },
    "summary_text": "Overall composite score: 74.5/100. Strong areas (1): Experience vs job minimum. ..."
  }
}
```

---

### `GET /api/candidates/`
List candidates. Auth required.

- Recruiter: all active candidates
- Candidate: only own profile

**Query params:**
- `search` — name or email search
- `min_experience` — minimum years
- `target_job_id` — filter by job application
- `job_id` — sort by AI score from latest ranking session
- `page`, `page_size` — pagination (default 10)

---

### `GET /api/candidates/<id>/`
Candidate detail with full ranking history and scoring_summary. Auth required.

**Query params:**
- `job_id` — live match dimensions for a specific job
- `no_live_dimensions=1` — skip live recomputation

**Response includes:**
- `ranking_history[]` — all past ranking sessions with `scoring_summary` per entry
- `match_dimensions_live` — live computed dimensions
- `scoring_summary` — from latest target_job ranking

---

### `PATCH /api/candidates/<id>/update/`
Update candidate. Auth required. Candidate can only update own.

---

### `DELETE /api/candidates/<id>/delete/`
Deactivate candidate. Recruiter only.

---

## 3. Jobs (`/api/jobs/`)

### `GET /api/jobs/`
List all active jobs. Auth required.

### `GET /api/jobs/for-upload/`
Job list for CV upload dropdown (id + title only).

### `POST /api/jobs/create/`
Create a job. Recruiter only.

**Body:**
```json
{
  "title": "Senior Backend Developer",
  "company": "Acme Corp",
  "description": "...",
  "requirements": "...",
  "required_skills": ["Python", "Django", "PostgreSQL"],
  "preferred_skills": ["Docker", "AWS", "Redis"],
  "min_experience": 3,
  "salary_range": "80000-120000"
}
```

### `GET /api/jobs/<id>/`
Job detail.

### `PUT/PATCH /api/jobs/<id>/update/`
Update job. Recruiter only.

### `DELETE /api/jobs/<id>/delete/`
Delete job. Recruiter only.

---

## 4. Ranking (`/api/ranking/`)

> All ranking endpoints require **Recruiter** role (except `preview` which requires auth).

---

### `POST /api/ranking/run/`
Run AI ranking for a job. Recruiter only.

**Body:**
```json
{
  "job_id": 1,
  "candidate_ids": [1, 2, 3],   // optional; defaults to all active candidates
  "only_target_job_candidates": true,  // only candidates who applied for this job
  "notes": "Q1 2026 hiring batch"
}
```

**Response:**
```json
{
  "message": "Ranking completed successfully",
  "session": { "id": 5, "job": 1, "job_title": "Senior Backend Dev", ... },
  "rankings_count": 12,
  "top_candidates": [
    {
      "id": 8,
      "candidate": { "id": 3, "name": "Alice Johnson", ... },
      "ai_score": 87.4,
      "ai_rank": 1,
      "matched_skills": ["Python", "Django", "PostgreSQL"],
      "missing_skills": ["Redis"],
      "explanation": "Overall match index: 87.4/100...",
      "scoring_summary": {
        "composite_score": 87.4,
        "overall_tier": "strong",
        "overall_label": "Strong Match",
        "strong": [...],
        "average": [...],
        "weak": [...],
        "summary_text": "..."
      },
      "human_decision": "pending",
      "email_sent": false
    }
  ]
}
```

---

### `GET /api/ranking/<job_id>/`
Get rankings for a job. Recruiter only.

**Query params:**
- `session_id` — specific session (defaults to latest)
- `min_score` — filter by minimum ai_score
- `human_decision` — filter: `pending | accepted | rejected | shortlisted`
- `ordering` — `rank` (default) or `-score`

**Response includes full `scoring_summary` per ranking with strong/average/weak breakdown.**

---

### `GET /api/ranking/details/<pk>/`
Detailed single ranking with full `scoring_summary`. Recruiter only.

**scoring_summary structure:**
```json
{
  "composite_score": 87.4,
  "overall_tier": "strong",        // "strong" | "average" | "weak"
  "overall_label": "Strong Match",
  "strong": [                      // score >= 75
    {
      "id": "semantic_alignment",
      "label": "Semantic alignment (job ↔ CV text)",
      "score": 82.0,
      "weight_pct": 32,
      "weighted_contribution": 26.24,
      "reason": "Semantic similarity between job text and CV embedding text is 82.0/100 ..."
    }
  ],
  "average": [ ... ],              // 50 <= score < 75
  "weak": [ ... ],                 // score < 50
  "counts": { "strong": 3, "average": 1, "weak": 1 },
  "summary_text": "Overall composite score: 87.4/100. Strong areas (3): ..."
}
```

---

### `POST /api/ranking/<ranking_id>/override/`
Human override of AI ranking. Recruiter only.

**Body:**
```json
{
  "human_decision": "accepted",     // pending | accepted | rejected | shortlisted
  "human_score": 92.0,              // optional override score (0-100)
  "human_feedback": "Excellent cultural fit despite missing Redis experience."
}
```

---

### `POST /api/ranking/<ranking_id>/accept/`
Accept a candidate and send personalised acceptance email via SMTP. **Recruiter only.**

Auto-generates email from:
- Candidate's matched skills
- Strong scoring dimensions with exact scores and reasons

**Body (optional):**
```json
{
  "extra_message": "Please expect a call from our HR team on Monday."
}
```

**Response 200:**
```json
{
  "message": "Acceptance email sent to jane@example.com.",
  "candidate": "Jane Smith",
  "job": "Senior Backend Developer",
  "email_sent_to": "jane@example.com",
  "ranking": { ..., "email_sent": true, "email_type": "accept", "human_decision": "accepted" }
}
```

**Error 502** if SMTP is not configured or sending fails.

---

### `POST /api/ranking/<ranking_id>/reject/`
Reject a candidate with specific reasons — sends detailed rejection email. **Recruiter only.**

If `rejection_reasons` not provided, auto-generated from weak/average scoring dimensions.

**Body:**
```json
{
  "rejection_reasons": [
    {
      "dimension": "Required skills coverage",
      "score": 33.3,
      "reason": "Required skills: 1/3 explicit matches (Python). Missing required: Django, React.",
      "missing": ["Django", "React"]
    },
    {
      "dimension": "Experience vs job minimum",
      "score": 46.0,
      "reason": "Experience gap: candidate 1 y vs minimum 3 y (2 year shortfall)."
    }
  ],
  "extra_message": "We encourage you to gain more experience with Django and React."
}
```

**Response 200:**
```json
{
  "message": "Rejection email sent to candidate@example.com.",
  "candidate": "Bob Jones",
  "job": "Senior Backend Developer",
  "email_sent_to": "candidate@example.com",
  "rejection_reasons_sent": [...],
  "ranking": { ..., "email_sent": true, "email_type": "reject", "human_decision": "rejected" }
}
```

---

### `POST /api/ranking/preview/`
Preview match score for a single job+candidate pair without saving a session. Auth required.

**Body:**
```json
{ "job_id": 1, "candidate_id": 3 }
```

---

### `GET /api/ranking/analytics/`
Ranking analytics. Recruiter only.

**Query params:** `job_id`, `days` (default 30)

---

### `GET /api/ranking/sessions/`
List ranking sessions. Recruiter only.

**Query params:** `job_id`, `min_candidates`, `ordering`

---

## 5. Audit (`/api/audit/`)

### `GET /api/audit/`
List audit logs. Recruiter only.

### `GET /api/audit/statistics/`
Audit statistics. Recruiter only.

---

## 6. Environment Configuration

Copy `.env.example` to `.env` and configure:

```env
# Django
SECRET_KEY=your_secret_key_here
DEBUG=True
API_REQUIRE_AUTH=true

# AI Keys
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...         # optional fallback

# SMTP Email (for accept/reject notifications)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password

# For Gmail: create App Password at Google Account → Security → App Passwords
# (only available if 2-Step Verification is enabled)

DEFAULT_FROM_EMAIL=AI CV System <your_email@gmail.com>
FRONTEND_URL=http://localhost:3000
```

**For local development** (email prints to console instead of sending):
```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

---

## 7. Scoring Logic

### How scores are computed

5 weighted dimensions, total weight = 1.0:

| Dimension | Weight | How calculated |
|---|---|---|
| Semantic alignment | 32% | Cosine similarity between CV embedding and job description embedding |
| Required skills | 28% | `matched_required / total_required * 100` |
| Preferred skills | 12% | `matched_preferred / total_preferred * 100` |
| Experience fit | 18% | 100 if meets minimum; penalized by 18pts per year shortfall |
| Education signals | 10% | Keyword match between education text and job description |

### Score tier classification

| Score | Tier | Label |
|---|---|---|
| ≥ 75 | `strong` | Strong Match |
| 50–74 | `average` | Average Match |
| < 50 | `weak` | Weak Match |

### Why summary_text shows specific reasons

Each dimension entry in `scoring_summary` includes:
- `score` — exact numeric score (0–100)
- `weight_pct` — how much this dimension counts toward total
- `weighted_contribution` — actual points contributed
- `reason` — human-readable explanation of why this score was given
- `matched` / `missing` — exact skill lists (for skills dimensions)

---

## 8. Frontend Integration Guide

### Login flow
```
POST /api/auth/login/ → { token, user: { role } }
Store token in localStorage/cookie.
Send on every request: Authorization: Token <token>
```

### Candidate flow
```
1. Register as candidate: POST /api/auth/register/ { role: "candidate", ... }
2. Upload CV: POST /api/candidates/upload/ with cv_file + job_id
   → Returns instant score, scoring_summary, matched/missing skills
3. View own profile: GET /api/candidates/  (shows only own)
```

### Recruiter flow
```
1. Login as recruiter
2. Create jobs: POST /api/jobs/create/
3. Run ranking: POST /api/ranking/run/ { job_id, only_target_job_candidates: true }
4. View rankings: GET /api/ranking/<job_id>/
   → Each ranking has scoring_summary with strong/average/weak breakdown
5. Override score: POST /api/ranking/<id>/override/ { human_score, human_decision }
6. Accept candidate: POST /api/ranking/<id>/accept/  → Email sent automatically
7. Reject candidate: POST /api/ranking/<id>/reject/ { rejection_reasons }  → Detailed email sent
```

---

## 9. Running the Project

```bash
cd ai_cv_system
python -m venv env
source env/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
