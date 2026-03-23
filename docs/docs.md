# AI CV System — Operations Guide

This guide explains **how to run** the backend, **what each major part does**, and **what rankings depend on** when you read API results. It complements **`README.md`** (architecture and code documentation) and **`API.md`** (endpoint details).

---

## 1. Prerequisites

- **Python 3.10+** (3.11 recommended)
- **pip** and a virtual environment (recommended)
- Optional: **OpenAI API key** for real embeddings and OpenAI-based CV parsing
- Optional: **Google Gemini API key** for the alternative file pipeline

---

## 2. Local setup

### 2.1 Create environment

From the `ai_cv_system` directory:

```bash
python -m venv env
source env/bin/activate   # Windows: env\Scripts\activate
pip install -r requirements.txt
```

### 2.2 Environment file

Copy or create **`.env`** in the **`ai_cv_system`** folder (same level as `manage.py`). The app loads it via `config/settings.py` using `BASE_DIR`.

Minimal example:

```env
SECRET_KEY=your-secret-key
DEBUG=True
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
```

If **`OPENAI_API_KEY`** is missing, embeddings fall back to a **dummy** mode: ranking still runs, but **semantic similarity** is not meaningful for production decisions—use only for UI wiring tests.

### 2.3 Database and static files

```bash
python manage.py migrate
python manage.py createsuperuser   # optional, for admin and token user
```

Development database defaults to **`db.sqlite3`** in the project root.

### 2.4 Run the server

```bash
python manage.py runserver 0.0.0.0:8000
```

- **Admin**: `http://127.0.0.1:8000/admin/`
- **API root**: `http://127.0.0.1:8000/api/...`

### 2.5 CORS (browser frontends)

Allowed origins are configured in **`config/settings.py`** (`_default_cors_origins` and optional `CORS_ALLOWED_ORIGINS`). Add your production SPA origin (e.g. Netlify) to defaults or to the environment variable as a comma-separated list.

---

## 3. What each major component does

| Component | Role in operations |
|-----------|-------------------|
| **Candidates app** | Upload CVs, list/filter candidates, retrieve detail with optional **ranking history** and **live match dimensions** for a job. |
| **Jobs app** | Define jobs: description, requirements text, **`required_skills`** / **`preferred_skills`** arrays, **`min_experience`**. Job text is embedded for semantic matching. |
| **Ranking app** | **Run** a batch ranking for one job (`POST /api/ranking/run/`), **preview** a single pair without saving a session, **read** latest rankings per job, **human override** on a row, **analytics**. |
| **Embedding service** | Lazily builds **job** and **candidate** vectors; used for the **semantic_alignment** dimension. |
| **Explanation service** | Builds **`match_breakdown`** (dimensions, weights, composite score) and narrative text. |
| **Audit app** | Records notable actions (e.g. ranking runs) when integrated. |

---

## 4. Typical workflows

### 4.1 Create a job

Use the jobs API or Django admin to create a **Job** with:

- Clear **`description`** and **`requirements`** (they feed the job embedding and HR context).
- Structured **`required_skills`** and **`preferred_skills`** (strings must match how you expect them to appear on candidate profiles for **literal** skill overlap).
- **`min_experience`** aligned with your bar (years).

Poor skill lists or empty lists reduce the usefulness of the **required_skills** / **preferred_skills** dimensions (neutral defaults apply when lists are empty).

### 4.2 Upload candidates

Use **`POST /api/candidates/upload/`** (see **`API.md`**) with optional **`job_id`** to associate a **target job** for convenience. The pipeline extracts text, fills **skills**, **experience_years**, **education**, etc. Quality of extraction directly affects skill matching and education heuristics.

### 4.3 Run a ranking session

Call **`POST /api/ranking/run/`** with the target **`job_id`** (and optional filters for which candidates to include, per your API contract). The backend:

1. Ensures **embeddings** exist for the job and candidates (may call OpenAI or use dummy mode).
2. Scores each candidate with the **same** explainable formula (see section 5).
3. Sorts by **composite score** and writes **`RankingSession`** + **`CandidateRanking`** rows.

Retrieve results with **`GET /api/ranking/<job_id>/`** (latest session for that job—confirm exact behavior in **`API.md`**).

### 4.4 Inspect one candidate vs one job

- **Preview (no DB session)**: use ranking **preview** endpoint if available (`/api/ranking/preview/`) — see **`API.md`**.
- **Candidate detail**: **`GET /api/candidates/<id>/`** may include **`ranking_history`** (past sessions with stored **`match_breakdown`**) and **`match_dimensions_live`** when **`job_id`** is passed or **`target_job`** is set—useful to see **dimensions** without running a full session.

---

## 5. What rankings are based on (reading results)

When you see **`ai_score`**, **`ai_rank`**, or **`match_breakdown`**, interpret them as follows.

### 5.1 Single source of ordering

Within one **ranking session**, ordering is by **`ai_score`** descending (ties are rare; implementation uses float ordering). **`ai_rank`** is the position after sorting (1 = best).

### 5.2 What `ai_score` is

**`ai_score`** is the **composite score** (0–100), **not** a raw embedding distance. It is:

\[
\sum_{\text{dimensions}} (\text{score on dimension}) \times (\text{weight})
\]

Weights are fixed in code (`MATCH_DIMENSION_WEIGHTS`); see **`README.md`** for the table.

### 5.3 Dimension checklist (what to trust)

| Dimension | You should know |
|-----------|-----------------|
| **Semantic alignment** | Depends on **OpenAI embeddings** when the API key is set. Reflects text similarity, **not** fact-checking. |
| **Required / preferred skills** | **String overlap** between job skill arrays and **candidate.skills** (from parsing). Typos or synonyms may not match. |
| **Experience fit** | Compares **numbers** on the candidate profile vs **`min_experience`**. |
| **Education signals** | **Keyword heuristic** only—not verification of degrees. |

### 5.4 What is explicitly not used in scoring

The dimension logic is designed so that **gender, age, ethnicity, and religion** are **not** inputs to these scores. Optional **fairness / proxy** scans on the candidate record inform notices and flags but do not drive the weighted composite in the same way as the five dimensions above (see code for **`merge_bias_flags_for_ranking`** behavior).

### 5.5 Human-in-the-loop

Stored fields such as **`human_decision`**, **`human_score`**, and review timestamps exist for **HR override** workflows. The AI output remains **advisory** until your process records a human decision.

---

## 6. Production notes

- Set **`DEBUG=False`**, use a strong **`SECRET_KEY`**, and restrict **`ALLOWED_HOSTS`** appropriately (currently permissive in default settings—tighten for real deployments).
- Use **`CORS_ALLOWED_ORIGINS`** for exact frontend URLs; avoid `*` with credentials.
- For PythonAnywhere or similar: configure **static/media**, **HTTPS**, and **reload** after code or `.env` changes.
- If embeddings are dummy, document internally that **semantic** ranks are for testing only.

---

## 7. Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| All candidates get similar scores | Dummy embeddings, or very generic job/candidate text. |
| Skills always “missing” | Job skills not listed, or naming mismatch vs extracted candidate skills. |
| `match_dimensions_live` error | Missing embedding API key, network failure, or empty `extracted_text`. |
| Ranking session empty / wrong job | Wrong `job_id`, inactive job filter, or no candidates in queryset. |

---

## 8. Further reading

- **`../README.md`** — Architecture, module list, scoring formula reference.
- **`API.md`** — Request/response examples and query parameters.
