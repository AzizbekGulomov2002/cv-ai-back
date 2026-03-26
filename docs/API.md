# AI CV System — Full API Reference

**Base URL:** `http://localhost:8000`  
**Auth header:** `Authorization: Token <token>`  
**Default Content-Type:** `application/json`  
**File uploads:** `multipart/form-data`

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Jobs](#2-jobs)
3. [Candidates / CV Upload](#3-candidates--cv-upload)
4. [Ranking & AI Scoring](#4-ranking--ai-scoring)
5. [Statistics Dashboard](#5-statistics-dashboard)
6. [Environment Configuration](#6-environment-configuration)
7. [Frontend Integration Guide](#7-frontend-integration-guide)

---

## 1. Authentication

**Base path:** `/api/auth/`

### Roles

| Role | Description |
|---|---|
| `recruiter` | Full access — manage jobs, view all candidates, run ranking, send emails |
| `candidate` | Upload own CV, browse jobs, view own profile and ranking results |

---

### `POST /api/auth/register/`

Register a new user. **Open — no auth required.**  
Supports `multipart/form-data` for profile image upload.

**Request (JSON or multipart form-data):**

| Field | Type | Required | Notes |
|---|---|---|---|
| `username` | string | ✓ | Unique username |
| `email` | string | ✓ | Valid email address |
| `password` | string | ✓ | Min 8 characters |
| `password_confirm` | string | ✓ | Must match `password` |
| `role` | string | ✓ | `recruiter` or `candidate` |
| `first_name` | string | | Candidate: recommended |
| `last_name` | string | | Candidate: recommended |
| `github` | string (URL) | | Candidate: GitHub profile URL |
| `image` | file | | Profile photo (PNG/JPG) |
| `company` | string | | Recruiter: company name |
| `phone` | string | | Phone number |

**Response 201:**
```json
{
  "message": "User registered successfully",
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "user": {
    "id": 5,
    "username": "ali_nazarov",
    "email": "ali@example.com",
    "first_name": "Ali",
    "last_name": "Nazarov",
    "role": "candidate",
    "company": "",
    "phone": "",
    "image": "user_images/5/profile.png",
    "image_url": "http://localhost:8000/media/user_images/5/profile.png",
    "github": "https://github.com/ali",
    "date_joined": "2026-03-26T12:00:00Z",
    "last_login": "2026-03-26T12:00:00Z",
    "candidate_profile": null
  }
}
```

**Error 400:** `{ "error": "Invalid registration data", "details": { "username": ["..."] } }`

---

### `POST /api/auth/login/`

Login with username + password. **Open — no auth required.**

**Request:**
```json
{ "username": "ali_nazarov", "password": "SecurePass123" }
```

**Response 200:**
```json
{
  "message": "Login successful",
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "user": {
    "id": 5,
    "username": "ali_nazarov",
    "email": "ali@example.com",
    "first_name": "Ali",
    "last_name": "Nazarov",
    "role": "candidate",
    "company": "",
    "phone": "",
    "image": "user_images/5/profile.png",
    "image_url": "http://localhost:8000/media/user_images/5/profile.png",
    "github": "https://github.com/ali",
    "date_joined": "2026-03-26T11:00:00Z",
    "last_login": "2026-03-26T12:05:00Z",
    "candidate_profile": {
      "id": 3,
      "name": "Ali Nazarov",
      "email": "ali@example.com",
      "phone": "",
      "github": "https://github.com/ali",
      "skills": ["Python", "Django"],
      "experience_years": 3,
      "education": "BSc Computer Science",
      "professional_summary": "...",
      "cv_file_url": "http://localhost:8000/media/cvs/3/cv.pdf",
      "is_active": true,
      "target_job_id": 2,
      "created_at": "2026-03-25T09:00:00Z",
      "updated_at": "2026-03-26T10:00:00Z"
    }
  }
}
```

> `candidate_profile` is `null` until the user uploads a CV.  
> `image_url` is an absolute URL ready to use as `<img src="...">`.

**Error 400:** `{ "error": "Invalid login credentials", "details": {...} }`

---

### `POST /api/auth/logout/`

Invalidate the current auth token. **Auth required.**

**Response 200:** `{ "message": "Logout successful" }`

---

### `GET /api/auth/me/`

Get the full profile of the currently logged-in user. **Auth required.**  
Use this on page load to restore session state.

**Response 200:** Same structure as `user` object in the login response above.

---

### `GET /api/auth/profile/`

Same as `/me/` — full user profile. **Auth required.**

---

### `PATCH /api/auth/profile/update/`

Update own profile fields. **Auth required.**  
Supports `multipart/form-data` for image. All fields optional (partial update).

**Request (PATCH, JSON or multipart):**
```json
{
  "first_name": "Ali",
  "last_name": "Nazarov",
  "email": "ali@example.com",
  "github": "https://github.com/ali",
  "company": "TechCorp",
  "phone": "+998901234567",
  "image": "<file>"
}
```

**Response 200:** Full user profile object (same as `/me/`).

---

### `PATCH /api/auth/profile/image/`

Upload or replace the profile photo only. **Auth required.**  
Must use `multipart/form-data`.

**Form field:** `image` (PNG/JPG/GIF file)

**Response 200:**
```json
{
  "message": "Profile image updated.",
  "user": { "...full user profile..." }
}
```

**Error 400:** `{ "error": "No image file provided. Use form field 'image'." }`

---

## 2. Jobs

**Base path:** `/api/jobs/`

---

### `GET /api/jobs/`

List all active jobs. **Auth required.**

- Recruiter: sees `applicants_count` per job.
- Candidate: sees `has_applied`, `my_score`, `my_status` for their own application.

**Response 200:**
```json
[
  {
    "id": 1,
    "title": "Backend Developer",
    "description": "We are looking for...",
    "requirements": "Python, Django, REST APIs",
    "required_skills": ["Python", "Django", "PostgreSQL"],
    "min_experience_years": 2,
    "is_active": true,
    "created_at": "2026-03-01T00:00:00Z",
    "applicants_count": 12,
    "has_applied": true,
    "my_score": 78.5,
    "my_status": "ranked"
  }
]
```

---

### `GET /api/jobs/<id>/`

Get job detail. **Auth required.**

---

### `GET /api/jobs/for-upload/`

List jobs for CV upload dropdown (id + title only). **Auth required.**

**Response 200:**
```json
[{ "id": 1, "title": "Backend Developer" }]
```

---

### `GET /api/jobs/<id>/apply-info/`

Get job details with the candidate's own application status. **Auth required (candidate).**

**Response 200:**
```json
{
  "job": {
    "id": 1,
    "title": "Backend Developer",
    "description": "...",
    "requirements": "...",
    "required_skills": ["Python", "Django"],
    "min_experience_years": 2
  },
  "my_application": {
    "has_applied": true,
    "candidate_id": 3,
    "status": "ranked",
    "score": 78.5,
    "rank": 2,
    "email_sent": false,
    "scoring_summary": {
      "composite_score": 78.5,
      "strong": [
        { "dimension": "skills", "score": 85.0, "reason": "Strong Python/Django alignment" }
      ],
      "average": [
        { "dimension": "experience", "score": 62.0, "reason": "2 years, meets minimum" }
      ],
      "weak": [
        { "dimension": "education", "score": 45.0, "reason": "No formal CS degree on file" }
      ]
    }
  }
}
```

---

### `GET /api/jobs/my-applications/`

List all jobs the current candidate has applied to. **Auth required (candidate).**

**Response 200:**
```json
[
  {
    "job_id": 1,
    "job_title": "Backend Developer",
    "applied_at": "2026-03-20T14:00:00Z",
    "status": "ranked",
    "score": 78.5,
    "rank": 2,
    "email_sent": false,
    "email_type": null
  }
]
```

---

### `POST /api/jobs/create/`

Create a new job posting. **Recruiter only.**

**Request:**
```json
{
  "title": "Backend Developer",
  "description": "We are looking for a senior backend engineer...",
  "requirements": "Python, Django, REST APIs, PostgreSQL",
  "required_skills": ["Python", "Django", "PostgreSQL"],
  "min_experience_years": 2,
  "is_active": true
}
```

**Response 201:** Created job object.

---

### `PATCH /api/jobs/<id>/update/`

Update a job posting. **Recruiter only.**

---

### `DELETE /api/jobs/<id>/delete/`

Delete a job posting. **Recruiter only.**  
**Response 204:** No content.

---

## 3. Candidates / CV Upload

**Base path:** `/api/candidates/`

---

### `POST /api/candidates/upload/`

Upload a CV linked to a job. **Auth required.**  
Must use `multipart/form-data`.

**Candidate users:** `name`, `email`, `github` are auto-filled from their user account.  
**Candidate users:** cannot upload if they already have an active CV (`is_active=true`) for the same job.

**Form fields:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `cv_file` | file | ✓ | PDF or DOCX |
| `job_id` | integer | | Link to job posting |
| `name` | string | | Auto-filled for candidates |
| `email` | string | | Auto-filled for candidates |
| `phone` | string | | |
| `github` | string | | Auto-filled for candidates |
| `skills` | JSON string | | e.g. `["Python","Django"]` |
| `experience_years` | integer | | |
| `education` | string | | |
| `professional_summary` | string | | |

**Response 201:**
```json
{
  "message": "CV uploaded successfully",
  "candidate_id": 7,
  "name": "Ali Nazarov",
  "job_id": 1,
  "scoring_summary": {
    "composite_score": 78.5,
    "strong": [...],
    "average": [...],
    "weak": [...]
  }
}
```

---

### `GET /api/candidates/`

List candidates. **Auth required.**

- Recruiter: sees all candidates.
- Candidate: sees only their own profile.

**Response 200:**
```json
[
  {
    "id": 7,
    "name": "Ali Nazarov",
    "email": "ali@example.com",
    "phone": "",
    "github": "https://github.com/ali",
    "skills": ["Python", "Django"],
    "experience_years": 3,
    "education": "BSc CS",
    "professional_summary": "...",
    "cv_file": "cvs/7/cv.pdf",
    "is_active": true,
    "target_job_id": 1,
    "candidate_user_id": 5,
    "created_at": "2026-03-25T09:00:00Z",
    "updated_at": "2026-03-26T10:00:00Z"
  }
]
```

---

### `GET /api/candidates/<id>/`

Get candidate detail. **Auth required.**

- Recruiter: any candidate.
- Candidate: own profile only.

Includes `scoring_summary` if a ranking exists for the candidate.

---

### `PATCH /api/candidates/<id>/update/`

Update candidate profile. **Auth required.**

- Recruiter: can update any candidate.
- Candidate: own profile only.

**Request:** Any subset of candidate fields (multipart for new CV file).

---

### `DELETE /api/candidates/<id>/delete/`

Delete candidate. **Recruiter only.**  
**Response 204:** No content.

---

## 4. Ranking & AI Scoring

**Base path:** `/api/ranking/`

All ranking endpoints are **Auth required**. Mutation endpoints are **Recruiter only**.

---

### `POST /api/ranking/run/`

Run AI ranking for all active candidates for a job. **Recruiter only.**

**Request:**
```json
{ "job_id": 1, "force_rerun": false }
```

**Response 200:**
```json
{
  "session_id": 12,
  "job_id": 1,
  "candidates_ranked": 8,
  "top_candidates": [
    {
      "rank": 1,
      "candidate_id": 7,
      "name": "Ali Nazarov",
      "score": 91.2,
      "status": "ranked",
      "scoring_summary": {
        "composite_score": 91.2,
        "strong": [
          { "dimension": "skills", "score": 95.0, "reason": "Excellent skills match" },
          { "dimension": "experience", "score": 88.0, "reason": "5 years, exceeds requirement" }
        ],
        "average": [
          { "dimension": "cultural_fit", "score": 70.0, "reason": "Good alignment with company values" }
        ],
        "weak": []
      }
    }
  ]
}
```

---

### `POST /api/ranking/preview/`

Preview match score between one candidate and one job without saving. **Auth required.**

**Request:**
```json
{ "candidate_id": 7, "job_id": 1 }
```

**Response 200:**
```json
{
  "composite_score": 78.5,
  "dimensions": {
    "skills": 85.0,
    "experience": 72.0,
    "education": 60.0,
    "summary": 80.0
  },
  "scoring_summary": { "strong": [...], "average": [...], "weak": [...] },
  "match_breakdown": { "matched_skills": [...], "missing_skills": [...] }
}
```

---

### `GET /api/ranking/<job_id>/`

Get all rankings for a job (latest session unless `session_id` is passed). **Recruiter only.**

Har bir `rankings[]` elementida:

- **`ai_rank`** / **`rank_position`** — butun o‘rin (1 = eng yuqori composite ball).
- **`rank`** — **0–100** leaderboard balli, DB da saqlanadi: `100 * (N - pos + 1) / N` (N = `session_total`, pos = `ai_rank`). Masalan N=3: 1→100, 2→66.67, 3→33.33.
- **`session_total`** — shu sessiyada jami nomzod (`candidates_count`).
- **`explanation`** oxirida `LEADERBOARD_CONTEXT`: `leaderboard_rank_0_100`, `position_in_session`.
- **`match_breakdown.rank`** / **`rank_position`** va **`scoring_summary`** dagi `rank` — 0–100 bilan mos.

**Misol (2-o‘rin, jami 3 nomzod):**

```json
{
  "id": 14,
  "ai_score": 50.17,
  "ai_rank": 2,
  "rank_position": 2,
  "rank": 66.6667,
  "session_total": 3,
  "final_score": 50.17,
  "candidate": { "id": 15, "name": "AZIZBEK GULOMOV" },
  "explanation": "... leaderboard_rank_0_100 ... 66.6667/100 (formula: 100*(N-pos+1)/N; pos=2, N=3) ...",
  "match_breakdown": {
    "rank": 66.6667,
    "rank_position": 2,
    "session_total": 3,
    "composite_score": 50.17
  }
}
```

**Potential Fit:** umumiy moslik foizi — **`final_score` / `ai_score`**; **leaderboard** o‘rni foizi — **`rank`** (0–100). Label “2 / 3” uchun `rank_position` + `session_total`.

---

### `GET /api/ranking/candidates/<candidate_id>/rank-history/`

Bitta nomzodning **barcha** ranking sessiyalaridagi natijalari (yangisidan eskisiga). **Recruiter only.**

**Response 200:**
```json
{
  "candidate_id": 15,
  "count": 2,
  "sessions": [
    {
      "ranking_id": 14,
      "session_id": 9,
      "session_created_at": "2026-03-26T11:58:35.332106Z",
      "job_id": 1,
      "job_title": "Backend engineer",
      "company": "Google",
      "ai_rank": 2,
      "rank_position": 2,
      "rank": 66.6667,
      "session_total": 3,
      "ai_score": 50.17,
      "final_score": 50.17,
      "human_decision": "pending"
    }
  ]
}
```

---

### `POST /api/ranking/<ranking_id>/override/`

Manually override the AI score. **Recruiter only.**

**Request:**
```json
{ "override_score": 85.0, "notes": "Strong cultural fit, slightly overriding AI score" }
```

**Response 200:**
```json
{
  "ranking_id": 45,
  "original_score": 91.2,
  "override_score": 85.0,
  "final_score": 85.0,
  "notes": "Strong cultural fit..."
}
```

---

### `POST /api/ranking/<ranking_id>/accept/`

Send acceptance email to candidate and mark as accepted. **Recruiter only.**

**Request:**
```json
{
  "custom_message": "We are delighted to invite you...",
  "position_details": "Senior Backend Developer, starting April 1st"
}
```

**Response 200:**
```json
{
  "message": "Acceptance email sent to ali@example.com",
  "ranking_id": 45,
  "status": "accepted",
  "email_sent": true,
  "email_sent_at": "2026-03-26T14:30:00Z"
}
```

> The email includes: candidate's name, matched strong skills, `scoring_summary.strong` items,
> job title, optional custom message, optional position details.

---

### `POST /api/ranking/<ranking_id>/reject/`

Send rejection email to candidate and mark as rejected. **Recruiter only.**

**Request:**
```json
{
  "reasons": [
    "Insufficient experience with PostgreSQL",
    "Portfolio does not demonstrate required scale"
  ],
  "custom_message": "We wish you success in your future applications."
}
```

> If `reasons` is omitted, the system auto-generates reasons from `scoring_summary.weak`
> and `scoring_summary.average` dimensions.

**Response 200:**
```json
{
  "message": "Rejection email sent to ali@example.com",
  "ranking_id": 45,
  "status": "rejected",
  "rejection_reasons": ["Insufficient experience with PostgreSQL", "..."],
  "email_sent": true,
  "email_sent_at": "2026-03-26T14:35:00Z"
}
```

---

### `GET /api/ranking/analytics/`

Ranking analytics summary across all jobs. **Recruiter only.**

**Query params:** `?job_id=1` (optional filter)

**Response 200:**
```json
{
  "total_ranked": 42,
  "avg_score": 67.4,
  "score_distribution": {
    "0-50": 8,
    "50-70": 14,
    "70-85": 15,
    "85-100": 5
  },
  "status_counts": { "ranked": 35, "accepted": 4, "rejected": 3 }
}
```

---

### `GET /api/ranking/sessions/`

List all ranking sessions. **Recruiter only.**

---

### `GET /api/ranking/details/<pk>/`

Get detail of a single `CandidateRanking` entry by PK. **Auth required.**

---

## 5. Statistics Dashboard

**Base path:** `/api/stats/`  
All stats endpoints are **Recruiter only**.

---

### `GET /api/stats/`

Full recruiter dashboard statistics.

**Query param:** `?days=30` (default: 30)

**Response 200:**
```json
{
  "overview": {
    "total_jobs": 5,
    "active_jobs": 4,
    "total_candidates": 42,
    "active_candidates": 38,
    "total_ranked": 35,
    "accepted": 4,
    "rejected": 3,
    "emails_sent": 7
  },
  "pipeline": {
    "uploaded": 42,
    "ranked": 35,
    "accepted": 4,
    "rejected": 3,
    "pending": 28
  },
  "per_job": [
    {
      "job_id": 1,
      "job_title": "Backend Developer",
      "candidates": 12,
      "ranked": 10,
      "avg_score": 71.3,
      "top_score": 91.2,
      "accepted": 1,
      "rejected": 2
    }
  ],
  "score_distribution": {
    "0-50": 8,
    "50-70": 14,
    "70-85": 15,
    "85-100": 5
  },
  "skills_gap": [
    { "skill": "PostgreSQL", "required_in_jobs": 3, "found_in_candidates": 8 }
  ],
  "time_trends": {
    "labels": ["2026-03-01", "2026-03-08", "2026-03-15", "2026-03-22"],
    "uploads": [5, 8, 12, 6],
    "rankings": [3, 7, 10, 5]
  },
  "top_candidates": [
    {
      "candidate_id": 7,
      "name": "Ali Nazarov",
      "best_score": 91.2,
      "applied_jobs": 2,
      "status": "ranked"
    }
  ],
  "users_summary": {
    "total_users": 20,
    "recruiters": 3,
    "candidates": 17,
    "new_this_period": 6
  },
  "email_stats": {
    "total_sent": 7,
    "accept_emails": 4,
    "reject_emails": 3,
    "pending_decisions": 28
  }
}
```

---

### `GET /api/stats/jobs/<job_id>/`

Detailed statistics for a single job. **Recruiter only.**

**Response 200:**
```json
{
  "job": { "id": 1, "title": "Backend Developer", "is_active": true },
  "ranking_sessions": [
    {
      "session_id": 12,
      "created_at": "2026-03-26T12:00:00Z",
      "candidates_count": 8
    }
  ],
  "latest_rankings": [
    {
      "rank": 1,
      "candidate_id": 7,
      "name": "Ali Nazarov",
      "score": 91.2,
      "status": "ranked"
    }
  ],
  "skills_gap": [
    { "skill": "PostgreSQL", "required": true, "matched_count": 5, "total_candidates": 8 }
  ]
}
```

---

## 6. Environment Configuration

Copy `.env.example` to `.env` and fill in all values:

```env
# Django
SECRET_KEY=your-very-secret-key
DEBUG=false
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (default: SQLite)
DATABASE_URL=sqlite:///db.sqlite3

# AI provider — use ONE of the two
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...

# API authentication (true = all endpoints require login)
API_REQUIRE_AUTH=true

# Email (SMTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
EMAIL_HOST_USER=your@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=AI CV System <your@gmail.com>

# Frontend URL (used in email links)
FRONTEND_URL=http://localhost:5173
```

### Gmail App Password Setup

1. Enable 2-Factor Authentication on your Google account.
2. Go to **Google Account → Security → App passwords**.
3. Generate an App Password for "Mail / Other device".
4. Use that as `EMAIL_HOST_PASSWORD`.

---

## 7. Frontend Integration Guide

### Session Restore (page load)

```js
const token = localStorage.getItem('token');
const res = await fetch('/api/auth/me/', {
  headers: { 'Authorization': `Token ${token}` }
});
const user = await res.json();
// user.role === 'candidate' || 'recruiter'
// user.image_url — absolute URL for <img>
// user.candidate_profile — linked CV data (or null)
```

---

### Candidate Registration with Photo

```js
const form = new FormData();
form.append('username', 'ali_nazarov');
form.append('email', 'ali@example.com');
form.append('password', 'SecurePass123');
form.append('password_confirm', 'SecurePass123');
form.append('role', 'candidate');
form.append('first_name', 'Ali');
form.append('last_name', 'Nazarov');
form.append('github', 'https://github.com/ali');
form.append('image', imageFileInput.files[0]);  // <input type="file">

const res = await fetch('/api/auth/register/', {
  method: 'POST',
  body: form   // no Content-Type header — browser sets it with boundary
});
const data = await res.json();
localStorage.setItem('token', data.token);
// data.user.image_url is available immediately
```

---

### Upload Profile Photo (after login)

```js
const form = new FormData();
form.append('image', fileInput.files[0]);

const res = await fetch('/api/auth/profile/image/', {
  method: 'PATCH',
  headers: { 'Authorization': `Token ${token}` },
  body: form
});
const data = await res.json();
// data.user.image_url — new absolute URL
```

---

### Candidate: Browse Jobs + CV Upload Flow

```
1. GET  /api/jobs/           → show job list (has_applied, my_score per job)
2. GET  /api/jobs/<id>/apply-info/  → show job detail + my current application status
3. POST /api/candidates/upload/ (multipart)  → upload CV for chosen job
4. GET  /api/jobs/my-applications/  → show all my applications history
```

---

### Candidate: CV Upload

```js
const form = new FormData();
form.append('cv_file', pdfFileInput.files[0]);
form.append('job_id', selectedJobId);
form.append('skills', JSON.stringify(['Python', 'Django']));
form.append('experience_years', '3');
form.append('education', 'BSc Computer Science');
form.append('professional_summary', 'Backend engineer with 3 years experience...');
// name, email, github auto-filled from user account

const res = await fetch('/api/candidates/upload/', {
  method: 'POST',
  headers: { 'Authorization': `Token ${token}` },
  body: form
});
const data = await res.json();
// data.scoring_summary.strong / .average / .weak
```

---

### Recruiter: Ranking + Decision Flow

```
1. POST /api/ranking/run/                     → run AI ranking for a job
2. GET  /api/ranking/<job_id>/                → view ranked candidates with scoring_summary
3. POST /api/ranking/<id>/override/           → adjust score if needed
4. POST /api/ranking/<id>/accept/             → send acceptance email
   POST /api/ranking/<id>/reject/             → send rejection email (auto or custom reasons)
5. GET  /api/stats/                           → dashboard overview
```

---

### Scoring Summary Structure

Every scoring result includes a `scoring_summary` object:

```json
{
  "composite_score": 78.5,
  "strong": [
    { "dimension": "skills", "score": 85.0, "reason": "Strong Python/Django alignment" }
  ],
  "average": [
    { "dimension": "experience", "score": 62.0, "reason": "2 years meets minimum" }
  ],
  "weak": [
    { "dimension": "education", "score": 45.0, "reason": "No formal CS degree on file" }
  ]
}
```

| Category | Score range | Meaning |
|---|---|---|
| `strong` | ≥ 75 | Clear strength — highlight in accept emails |
| `average` | 50 – 74 | Acceptable — context-dependent |
| `weak` | < 50 | Gap — used as basis for reject email reasons |

---

### HTTP Status Code Summary

| Code | Meaning |
|---|---|
| 200 | Success |
| 201 | Created |
| 204 | Deleted (no body) |
| 400 | Validation error — check `details` |
| 401 | Missing or invalid token |
| 403 | Insufficient role (e.g. candidate hitting recruiter endpoint) |
| 404 | Resource not found |
| 500 | Server error |

---

### Common Headers

```
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
Content-Type: application/json          (for JSON requests)
Content-Type: multipart/form-data       (for file uploads — set by browser/axios automatically)
```

> **Tip for Axios/fetch:** When uploading files with `FormData`, do **not** manually set `Content-Type`. Let the browser set it so the multipart boundary is included correctly.
