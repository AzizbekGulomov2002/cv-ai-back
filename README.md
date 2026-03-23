# AI CV System — Backend

A **Django REST Framework** backend that ingests CV files (PDF/DOCX), extracts structured profiles using **OpenAI** or **Google Gemini**, stores candidates and jobs, and produces **explainable match scores** and **rankings** using text embeddings plus rule-based dimensions. The system is designed for **HR decision-support** (not automated hiring), with transparency fields aligned to responsible-AI practices.

---

## Table of contents

1. [Features](#features)
2. [Architecture](#architecture)
3. [Technology stack](#technology-stack)
4. [Repository layout](#repository-layout)
5. [Core domain models](#core-domain-models)
6. [Services layer](#services-layer)
7. [Ranking & scoring (how results are produced)](#ranking--scoring-how-results-are-produced)
8. [API surface](#api-surface)
9. [Configuration (environment variables)](#configuration-environment-variables)
10. [Related documentation](#related-documentation)

---

## Features

- **CV upload & parsing**: Structured profile extraction (skills, experience, education, summaries) from uploaded files.
- **Embeddings**: Job text and CV-derived text embedded for semantic similarity (OpenAI `text-embedding-3-small` when `OPENAI_API_KEY` is set; otherwise a **dummy** embedding mode for development).
- **Explainable matching**: Five weighted **dimensions** (semantic alignment, required/preferred skills, experience fit, education heuristics) combine into a **composite score** (0–100).
- **Ranking sessions**: Batch rank active candidates for a job; persist `ai_score`, `ai_rank`, explanations, `match_breakdown`, and optional human review.
- **Audit & API actors**: Actions can be logged; anonymous API usage is supported where configured.
- **CORS**: Configurable allowed origins for SPA frontends (e.g. Netlify).

---

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Client    │────▶│  Django + DRF    │────▶│  SQLite (dev)   │
│  (SPA/API)  │     │  REST API        │     │  / Postgres     │
└─────────────┘     └────────┬─────────┘     └─────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
   ┌──────────┐      ┌──────────────┐    ┌─────────────┐
   │ OpenAI   │      │ Gemini       │    │ Embedding   │
   │ CV/JSON  │      │ (file API)   │    │ (OpenAI or  │
   │          │      │ fallback     │    │  dummy)     │
   └──────────┘      └──────────────┘    └─────────────┘
```

**Data flow (high level)**

1. **Upload** → file stored, text extracted, profile JSON applied to `Candidate` (skills, experience, education, `extracted_text`, optional `ai_profile_json`, fairness scan).
2. **Embeddings** → generated lazily when a job match or ranking run needs them (`EmbeddingService`).
3. **Match / rank** → `ExplanationService.compute_match_breakdown` + `RankingService.evaluate_candidate_for_job` → composite score; for a full run, candidates sorted by score → `RankingSession` + `CandidateRanking` rows.

---

## Technology stack

| Layer | Choice |
|-------|--------|
| Framework | Django 4.2, Django REST Framework 3.14 |
| Auth | Token auth (DRF), optional user for ranking/audit |
| HTTP | `django-cors-headers` |
| LLM / CV | OpenAI API; Google Generative AI (Gemini) for file-based pipeline |
| Embeddings | OpenAI Embeddings API (or deterministic dummy vectors if no key) |
| DB | SQLite by default (`db.sqlite3` under project root) |

---

## Repository layout

```
ai_cv_system/
├── config/                 # settings, urls, wsgi
├── apps/
│   ├── users/              # authentication API
│   ├── candidates/         # CV upload, list, detail, updates
│   ├── jobs/                 # job postings (requirements, skills, embeddings)
│   ├── ranking/              # sessions, per-candidate rankings, analytics endpoints
│   ├── ai/                   # embedding cache and related helpers
│   └── audit/                # audit logging
├── services/                 # business logic (see below)
├── docs/
│   ├── API.md                # endpoint reference (incl. Uzbek notes in places)
│   └── docs.md               # operations guide (English)
├── manage.py
├── requirements.txt
└── README.md                 # this file
```

---

## Core domain models

| Model | Responsibility |
|-------|----------------|
| **User** | Staff/API users; token authentication. |
| **Job** | Title, company, description, `requirements`, `required_skills`, `preferred_skills`, `min_experience`, embedding vector for the job text. |
| **Candidate** | Personal fields, CV file, parsed `skills`, `experience_years`, `education`, `extracted_text`, embedding vector, optional `target_job`, `fairness_scan_json`, `ai_profile_json`. |
| **RankingSession** | One ranking run for a **single** job: timestamp, creator, candidate count, notes. |
| **CandidateRanking** | One row per (session, candidate): `ai_score`, `ai_rank`, `matched_skills`, `missing_skills`, `explanation`, `bias_flags`, `match_breakdown` (full dimension breakdown), human review fields. |

---

## Services layer

| Service | Role |
|---------|------|
| **`EmbeddingService`** | Builds embeddings for job text and CV text; cosine similarity mapped to a 0–100-style signal; caches via `EmbeddingCache` when applicable. |
| **`ExplanationService`** | Computes **`match_breakdown`**: per-dimension scores, weights, weighted contributions, notices (human-in-the-loop, fairness). Merges bias-related flags with `fairness_scan_json`. |
| **`RankingService`** | Ensures embeddings, calls evaluation for each candidate, sorts by composite score, creates `RankingSession` and `CandidateRanking` records; analytics and optional human override hooks. |
| **`CVParserService` / `cv_file_extract` / `job_match_payload`** | CV parsing, structured extraction, and payloads for job–candidate evaluation UIs. |
| **`api_actor`** | Resolves the acting user (or anonymous API user) for auditing and attribution. |

---

## Ranking & scoring (how results are produced)

Rankings are **not** produced by a single opaque LLM score. The **primary sort key** is the **composite score** (0–100), computed as a **weighted sum** of five dimensions. Weights are defined in `services/explain_service.py` as `MATCH_DIMENSION_WEIGHTS` (sum = **1.0**).

| Dimension ID | Weight | What it measures |
|----------------|--------|-------------------|
| **semantic_alignment** | 0.32 | Cosine similarity between the **job embedding** (title + description + requirements) and the **candidate embedding** (from CV / extracted text), scaled to 0–100. Captures broad textual overlap, not verification of claims. |
| **required_skills** | 0.28 | Share of **job `required_skills`** that appear in the candidate’s **skills** list (case-insensitive matching). If the job has no required skills, a neutral default applies. |
| **preferred_skills** | 0.12 | Same idea for **`preferred_skills`**. |
| **experience_fit** | 0.18 | Compares **`candidate.experience_years`** to **`job.min_experience`**. Penalizes large shortfalls; missing experience on the profile uses a conservative score. |
| **education_signals** | 0.10 | Heuristic based on education-related keywords in the candidate’s education text vs. job text (not degree verification). |

**Composite score**

\[
\text{composite\_score} = \sum_i (\text{dimension\_score}_i \times \text{weight}_i)
\]

clamped to **[0, 100]**.

**Ranking order**

- For a **ranking run**, every selected candidate gets a composite score; candidates are sorted **descending** by score.
- **`ai_rank`** is **1** for the highest score, **2** for the next, and so on.
- **Protected attributes** (gender, age, ethnicity, religion) are **not** used as model inputs for these dimensions; notices and optional fairness scans document this for compliance-style UIs.

**Stored outputs**

Each `CandidateRanking` stores **`ai_score`** (the composite), **`ai_rank`**, **`match_breakdown`** (full structure including `dimensions`, `weights`, `composite_score`), narrative **`explanation`**, and skill lists for UI.

For **live** detail views, the API can **recompute** the same breakdown for a given job without creating a new session (see `docs/docs.md`).

---

## API surface

Base path: **`/api/`**

| Prefix | Purpose |
|--------|---------|
| `/api/auth/` | Registration, login, token |
| `/api/candidates/` | Upload, list, detail (includes optional `ranking_history`, `match_dimensions_live`) |
| `/api/jobs/` | Job CRUD and job-related data |
| `/api/ranking/` | Run ranking, preview match, list rankings by job, session list, human override, analytics |
| `/api/audit/` | Audit logs |

Detailed request/response shapes: **`docs/API.md`**.

---

## Configuration (environment variables)

Typical keys (see `config/settings.py` for full behavior):

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `true`/`false` |
| `OPENAI_API_KEY` | Enables OpenAI embeddings and CV flows that use OpenAI |
| `OPENAI_CV_MODEL` | CV extraction model (default `gpt-4o`) |
| `GEMINI_API_KEY` | Gemini-based CV / file pipeline |
| `CORS_ALLOWED_ORIGINS` | Comma-separated extra origins (merged with defaults in settings) |

---

## Related documentation

- **`docs/docs.md`** — How to install, run, and operate the system (workflows, ranking interpretation).
- **`docs/API.md`** — HTTP API reference.

---

## License / disclaimer

This software provides **decision-support** only. Hiring decisions should remain with qualified human reviewers. Scores and rankings are **heuristic** and depend on extraction quality, skill lists, and embedding availability.
