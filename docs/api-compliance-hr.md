# API — HR / EU AI Act compliance (explainability, fairness, human-in-the-loop)

**One-line:** Safe, explainable, auditable AI for hiring — **decision-support only**; HR **Accept / Reject / Shortlist** with audit trail.

## Principles (implemented)

| Talab | API / model |
|--------|-------------|
| Explainability (WHY not only score) | `match_breakdown.dimensions[]` + `explanation` text |
| Fairness transparency | `fairness_scan_json` on candidate; `bias_flags` on ranking |
| Human in the loop | `POST .../ranking/<id>/override/` — `human_decision`, `human_feedback` |
| Audit | `GET /api/audit/...` + actions logged on upload, ranking, preview, override |
| Documentation | This file + limitations below |

**Limitations (disclose in demos):** LLM extraction can miss scanned PDFs; embeddings are approximate; heuristic education/skill matching is not credential verification; **no automated hiring decision**.

---

## 1. CV upload — structured + fairness + compliance

`POST /api/candidates/upload/`  
`Content-Type: multipart/form-data` — field: `file` / `cv` / `cv_file`

**Ixtiyoriy:** `job_id` (form maydon yoki query `?job_id=1`) — yuklashdan keyin shu job uchun **score**, **skill_breakdown**, **matched/missing skills**, **explanation** (summary/details), **fairness**, **audit**, **rank** (oxirgi sessiyada bo‘lsa) qaytariladi. To‘liq DB obyekti avvalgidek `candidate` ichida; qisqa kartochka: `candidate_profile`.

### Response `201` (asosiy qismlar)

```json
{
  "message": "CV processed successfully (file pipeline)",
  "extraction_source": "gemini_file_api",
  "extracted_profile": {
    "full_name": "...",
    "skills": ["Python", "Django"],
    "fairness_scan": {
      "gender_proxy_detected": false,
      "gender_proxy_notes": null,
      "age_proxy_detected": false,
      "age_proxy_notes": null,
      "other_proxy_flags": []
    },
    "compliance": {
      "factors_used_for_profile": ["skills", "employment_history", "education"],
      "factors_not_used_for_automated_decision": ["gender", "age", "ethnicity", "religion"],
      "limitation_note": "..."
    },
    "skill_evidence": [{ "skill": "Python", "evidence": "Backend role at ..." }],
    "gemini_model": "gemini-2.5-flash",
    "source": "gemini_file_api"
  },
  "cv_parsed": { "...": "..." },
  "extracted_text": "...",
  "candidate": {
    "id": 1,
    "professional_summary": "...",
    "fairness_scan_json": { "...": "..." },
    "ai_profile_json": { "...": "..." },
    "skills": [],
    "experience_years": 2
  }
}
```

**Saved fields:** `Candidate.ai_profile_json` (full JSON), `fairness_scan_json`, `professional_summary`, `skills`, `education`, `extracted_text`, etc.

---

## 2. Job match preview (sessiyasiz — dashboard)

`POST /api/ranking/preview/`  
`Content-Type: application/json`

### Request

```json
{
  "job_id": 1,
  "candidate_id": 5
}
```

### Response `200`

```json
{
  "message": "Match preview (decision-support only; not a hiring decision).",
  "job": { "id": 1, "title": "Backend Developer" },
  "candidate": { "id": 5, "name": "Jane Doe" },
  "embedding_warnings": [],
  "match": {
    "composite_score": 78.4,
    "match_breakdown": {
      "schema_version": 1,
      "composite_score": 78.4,
      "weights": {
        "semantic_alignment": 0.32,
        "required_skills": 0.28,
        "preferred_skills": 0.12,
        "experience_fit": 0.18,
        "education_signals": 0.10
      },
      "dimensions": [
        {
          "id": "semantic_alignment",
          "label": "Semantic alignment (job ↔ CV text)",
          "score": 82.0,
          "weight": 0.32,
          "weighted_contribution": 26.24,
          "explanation": "Semantic similarity between job text and CV embedding text..."
        },
        {
          "id": "required_skills",
          "label": "Required skills coverage",
          "score": 85.0,
          "weight": 0.28,
          "weighted_contribution": 23.8,
          "explanation": "Required skills: 3/4 explicit matches...",
          "matched": ["Python", "Django"],
          "missing": ["Kubernetes"]
        }
      ],
      "human_in_the_loop_notice": "This score is decision-support only...",
      "fairness_notice": "Gender, age, ethnicity..."
    },
    "matched_skills": ["Python", "Django", "PostgreSQL"],
    "missing_skills": ["Kubernetes"],
    "explanation": "Overall match index: 78.4/100 ...",
    "bias_flags": ["transparency:gender_proxy_text_in_cv"]
  }
}
```

---

## 3. Run ranking (barcha nomzodlar yoki tanlanganlar)

`POST /api/ranking/run/`

### Request

```json
{
  "job_id": 1,
  "candidate_ids": [5, 6, 7],
  "notes": "Q1 hiring — explainable ranking"
}
```

`candidate_ids` ixtiyoriy; bo‘lmasa — barcha `is_active` nomzodlar.

### Response `200`

```json
{
  "message": "Ranking completed successfully",
  "session": { "id": 10, "job": 1, "candidates_count": 3 },
  "rankings_count": 3,
  "top_candidates": [
    {
      "id": 101,
      "ai_score": 78.4,
      "ai_rank": 1,
      "matched_skills": ["Python"],
      "missing_skills": ["Kubernetes"],
      "explanation": "Overall match index...",
      "bias_flags": [],
      "match_breakdown": { "dimensions": [], "composite_score": 78.4 },
      "human_decision": "pending",
      "candidate": { "id": 5, "name": "Jane Doe" }
    }
  ]
}
```

Har bir `CandidateRanking` da: `match_breakdown`, `explanation`, `bias_flags`, `human_decision` (default `pending`).

---

## 4. Job bo‘yicha so‘nggi ranking

`GET /api/ranking/<job_id>/`

Returns `session` + `rankings` (to‘liq serializer, `match_breakdown` bilan).

---

## 5. Human in the loop — override

`POST /api/ranking/<ranking_id>/override/`

### Request

```json
{
  "human_decision": "accepted",
  "human_score": 80.0,
  "human_feedback": "Strong backend fit; discuss Kubernetes upskilling in interview."
}
```

`human_decision`: `pending` | `accepted` | `rejected` | `shortlisted`

### Response `200`

```json
{
  "message": "Human override applied successfully",
  "ranking": {
    "id": 101,
    "human_decision": "accepted",
    "human_score": 80.0,
    "human_feedback": "...",
    "reviewed_at": "2026-03-22T12:00:00Z",
    "is_reviewed": true
  }
}
```

Audit: `override` action logged.

---

## 6. Analytics

`GET /api/ranking/analytics/?job_id=1&days=30`

---

## Scoring formula (short)

`composite_score` = sum over dimensions:  
`score_dimension × weight_dimension`  
(capped 0–100).  

**Not used as inputs:** gender, age, ethnicity, religion (policy text in `match_breakdown.fairness_notice` + LLM `compliance` object on candidate).

---

## Frontend checklist (hackathon demo)

1. Upload CV → show `fairness_scan` + `skill_evidence`.  
2. Preview match → show `dimensions` table (WHY).  
3. Run ranking → list with `ai_score` + expand `match_breakdown`.  
4. Override UI → `accepted` / `rejected` + feedback.  
5. Audit screen → filter by `ranking`, `override`, `upload`.
