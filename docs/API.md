# AI CV System — REST API (bitta hujjat)

**Base URL (lokal):** `http://127.0.0.1:8000`  
**Prefix:** `/api/`

Sukut: `API_REQUIRE_AUTH=false` — ko‘p endpointlar token talab qilmaydi. Production da `API_REQUIRE_AUTH=true`.

**English documentation:** project overview and scoring → [`../README.md`](../README.md); setup & operations → [`docs.md`](docs.md).

---

## 1. Auth (`/api/auth/`)

| Method | Path | Tavsif |
|--------|------|--------|
| POST | `/api/auth/register/` | Ro‘yxatdan o‘tish |
| POST | `/api/auth/login/` | Kirish (token qaytaradi) |
| POST | `/api/auth/logout/` | Chiqish |
| GET | `/api/auth/profile/` | Profil |
| PATCH/PUT | `/api/auth/profile/update/` | Yangilash |

---

## 2. Jobs — vakansiyalar (`/api/jobs/`)

| Method | Path | Tavsif |
|--------|------|--------|
| GET | `/api/jobs/` | Aktiv vakansiyalar. Query: `search`, `job_type`, `level`, `location` |
| **GET** | **`/api/jobs/for-upload/`** | **CV yuklash uchun tanlash ro‘yxati** + `ui_prompt` (uz/en) + `api` qisqa ko‘rsatma |
| POST | `/api/jobs/create/` | Yangi job |
| GET | `/api/jobs/<id>/` | Batafsil |
| PATCH/PUT | `/api/jobs/<id>/update/` | Yangilash (description o‘zgarsa embedding qayta hisoblanadi) |
| DELETE | `/api/jobs/<id>/delete/` | Deaktivlash |

**Ko‘p vakansiya + ko‘p nomzod oqimi:** avval `GET /api/jobs/for-upload/` yoki `GET /api/jobs/` dan `id` oling → har bir CV yuklashda shu `job_id` ni yuboring → nomzod `target_job` ga bog‘lanadi → ranking da `only_target_job_candidates: true` bilan faqat shu vakansiyaga yozilganlar saralanadi.

---

## 3. Candidates — nomzodlar (`/api/candidates/`)

### 3.1 CV yuklash

**POST** `/api/candidates/upload/`  
`Content-Type: multipart/form-data`

| Maydon | Majburiy | Tavsif |
|--------|----------|--------|
| `file` / `cv` / `cv_file` | ha | PDF yoki DOCX |
| `job_id` | **tavsiya** | Tanlangan vakansiya: moslik hisobi + DB da `target_job` bog‘lanishi |
| `name`, `email`, `phone` | yo‘q | Qo‘lda override |

Query alternativa: `POST /api/candidates/upload/?job_id=3`

**Natija (201):** to‘liq `candidate` (ichida `target_job`), ixtiyoriy `job_evaluation` / `score` / `matching.skill_match` va hokazo — job talablari **o‘sha paytdagi** `Job` yozuvidan olinadi (keyin job o‘zgarsa, qayta upload yoki qayta ranking).

### 3.2 Ro‘yxat

**GET** `/api/candidates/`

| Query | Tavsif |
|-------|--------|
| `page`, `page_size` | Sahifalash (**sukut page_size=10**) |
| `search` | ism/email |
| `min_experience` | minimal tajriba yili |
| **`target_job_id`** | **Faqat shu vakansiyaga biriktirilgan** nomzodlar |
| **`job_id`** | Shu job bo‘yicha **oxirgi ranking sessiyasi** `ai_score` bo‘yicha tartib (yuqoridan pastga). Meta: `ranking_session_applied`, `ranking_session_id` |
| `job_id` + ro‘yxat | Har bir element: `job_match_score`, `job_match_rank` (sessiyada bo‘lsa) |

### 3.3 Batafsil nomzod

**GET** `/api/candidates/<id>/`

| Query | Tavsif |
|-------|--------|
| `job_id` | Live **match_dimensions_live** shu job bo‘yicha hisoblanadi (talablar o‘zgarsa — yangilanadi) |
| `no_live_dimensions=1` | Live qayta hisoblamaslik (faqat DB dagi `ranking_history`) |

**Javobga qo‘shimcha maydonlar:**

- **`ranking_history`** — barcha saqlangan `CandidateRanking` yozuvlari (oxirgi birinchi): `session_id`, `job`, `ai_score`, `ai_rank`, `human_decision`, **`dimensions`**, **`match_breakdown`**, `composite_score_stored`, qisqa `explanation_preview`.
- **`match_dimensions_live`** — hozirgi job (query yoki `target_job`) bo‘yicha **yangi hisoblangan** `dimensions`, `weights`, `composite_score`, `matched_skills` / `missing_skills`.
- Agar `target_job` bo‘lsa va oxirgi sessiyada qatnashgan bo‘lsa: **`job_match_score`**, **`job_match_rank`**, **`latest_ranking_session_for_target_job`**.

### 3.4 Boshqa

| Method | Path |
|--------|------|
| PATCH/PUT | `/api/candidates/<id>/update/` |
| DELETE | `/api/candidates/<id>/delete/` (soft deactivate) |

---

## 4. Ranking (`/api/ranking/`)

### 4.1 Ishga tushirish

**POST** `/api/ranking/run/`

```json
{
  "job_id": 1,
  "candidate_ids": [2, 3, 5],
  "notes": "Q1 saralash",
  "only_target_job_candidates": false
}
```

| Maydon | Tavsif |
|--------|--------|
| `job_id` | majburiy |
| `candidate_ids` | ixtiyoriy; bo‘lmasa — barcha aktiv nomzodlar |
| **`only_target_job_candidates`** | **`true`** va `candidate_ids` bo‘lmasa → faqat `target_job_id == job_id` nomzodlar (bir vakansiyaga yozilganlar) |

### 4.2 Job bo‘yicha natijalar (filtrlar)

**GET** `/api/ranking/<job_id>/`

| Query | Tavsif |
|-------|--------|
| `session_id` | Aniq sessiya (aks holda oxirgi) |
| `min_score` | Minimal `ai_score` |
| `human_decision` | `pending`, `accepted`, `rejected`, `shortlisted` |
| `ordering` | `rank` (sukut) yoki `-score` / `score_desc` |

Javobda `filters_applied` va `rankings` (tushuntirish, `match_breakdown`, …).

### 4.3 Boshqa ranking endpointlar

| Method | Path | Tavsif |
|--------|------|--------|
| POST | `/api/ranking/preview/` | `job_id`, `candidate_id` — sessiyasiz moslik |
| POST | `/api/ranking/<ranking_id>/override/` | HR qarori: `human_decision`, `human_score`, `human_feedback` |
| GET | `/api/ranking/analytics/` | `job_id`, `days` |
| GET | `/api/ranking/sessions/` | Sessiyalar. Query: **`job_id`**, **`min_candidates`**, **`ordering`** (`-created_at` / `created_at`) |
| GET | `/api/ranking/details/<pk>/` | Bitta `CandidateRanking` |

---

## 5. Audit (`/api/audit/`)

| Method | Path | Query (ro‘yxat) |
|--------|------|-----------------|
| GET | `/api/audit/` | `action_type`, `risk_level`, `user_id`, `days`, `search` |
| GET | `/api/audit/statistics/` | `days` |

---

## 6. Multi-job workflow (qisqa)

1. **Vakansiyalar:** `GET /api/jobs/for-upload/` — dropdown uchun.  
2. **CV:** har nomzod uchun `POST .../candidates/upload/` + **FormData** `job_id=<tanlangan>`.  
3. **Saralash (faqat shu positsiyaga yozilganlar):**  
   `POST /api/ranking/run/` body: `{ "job_id": N, "only_target_job_candidates": true }`  
4. **Ko‘rish:** `GET /api/ranking/N/?ordering=rank&min_score=50`  
5. **Ro‘yxat (prioritet):** `GET /api/candidates/?job_id=N&page=1`

---

## 7. Cheklovlar

- AI ball **tavsiya**; yakuniy qaror HR (`override`).  
- Job `required_skills` / `description` o‘zgargach, aniq natija uchun ranking ni qayta ishlatish yoki CV ni qayta baholash kerak.  
- `rank` upload javobida faqat **mavjud ranking sessiyasida** bo‘lsa to‘liq.

---

## 8. Namuna vakansiyalar (rollar bo‘yicha)

Quyidagilar **`POST /api/jobs/create/`** uchun tayyor JSON (maydonlarni o‘z kompaniyangizga moslang).  
`application_deadline` ixtiyoriy — `null` yoki ISO8601, masalan `"2026-12-31T23:59:59Z"`.

### 8.1 Frontend Engineer

```json
{
  "title": "Senior Frontend Engineer",
  "company": "Nova Labs",
  "location": "Remote (UTC+3–+6) / Tashkent hub",
  "description": "We build a design-system-driven SaaS dashboard used by thousands of operators. You will own complex UI flows: tables with virtualization, filters, accessibility (WCAG 2.1 AA), and performance budgets. You work with product designers and backend engineers; code reviews and RFCs are part of the culture. We ship in two-week cycles; feature flags and gradual rollouts are standard.",
  "requirements": "- 4+ years shipping production web UIs.\n- Strong TypeScript and React (hooks, state patterns, error boundaries).\n- CSS at scale: design tokens, responsive layout, prefers reduced-motion awareness.\n- Experience with REST or GraphQL clients, optimistic updates, and loading/error UX.\n- Testing: Jest/React Testing Library or Vitest; basic E2E awareness (Playwright/Cypress).\n- English B2+ for docs and async communication.\n- Portfolio or links to shipped products appreciated.",
  "job_type": "full_time",
  "level": "senior",
  "required_skills": [
    "TypeScript",
    "React",
    "HTML/CSS",
    "REST API",
    "Git",
    "Responsive design",
    "Accessibility",
    "Jest or Vitest"
  ],
  "preferred_skills": [
    "Next.js",
    "TanStack Query",
    "Zustand or Redux Toolkit",
    "Storybook",
    "Vite",
    "Figma handoff",
    "Web performance",
    "i18n"
  ],
  "min_experience": 4,
  "max_experience": 12,
  "salary_min": "3500.00",
  "salary_max": "5200.00",
  "currency": "USD",
  "application_deadline": null
}
```

### 8.2 AI Engineer

```json
{
  "title": "AI / ML Engineer (LLM & Retrieval)",
  "company": "Nova Labs",
  "location": "Hybrid — Tashkent",
  "description": "You will design and ship LLM-powered features in production: structured extraction from documents, RAG over internal knowledge bases, and safe guardrails. Focus is on engineering—prompting, evaluation harnesses, latency/cost trade-offs, observability—not training foundation models from scratch. You collaborate with backend engineers to expose features via APIs and with compliance on logging and human-in-the-loop patterns.",
  "requirements": "- 3+ years software engineering; at least 1 year on ML or LLM application code in production.\n- Python; experience calling OpenAI/Anthropic/Google APIs with retries, timeouts, and JSON schema validation.\n- Prompt design, few-shot patterns, and basic eval sets (precision/recall mindset).\n- Vector DB or embeddings workflow (e.g. pgvector, Pinecone, Weaviate) at proof-of-concept or production level.\n- Understanding of PII, prompt injection risks, and refusal/safety basics.\n- English B2+; can read papers and internal RFCs.\n- BS in CS/DS or proven equivalent.",
  "job_type": "full_time",
  "level": "mid",
  "required_skills": [
    "Python",
    "LLM APIs",
    "Prompt engineering",
    "REST API",
    "Git",
    "Embeddings or RAG",
    "JSON schema validation",
    "Evaluation mindset"
  ],
  "preferred_skills": [
    "LangChain or LlamaIndex",
    "OpenAI SDK",
    "PostgreSQL pgvector",
    "Docker",
    "FastAPI",
    "pytest",
    "Weights & Biases or MLflow",
    "EU AI Act awareness"
  ],
  "min_experience": 3,
  "max_experience": 10,
  "salary_min": "4000.00",
  "salary_max": "6500.00",
  "currency": "USD",
  "application_deadline": null
}
```

### 8.3 Team Lead (Engineering)

```json
{
  "title": "Engineering Team Lead — Platform Squad",
  "company": "Nova Labs",
  "location": "Tashkent + remote-friendly",
  "description": "You lead a cross-functional squad (4–6 engineers) delivering the core API and shared services. You balance delivery with quality: architecture reviews, on-call rotation design, and growing engineers through 1:1s and clear expectations. You still code in critical paths (~30% time). You partner with PM on roadmap sequencing and with HR on hiring loops for your team.",
  "requirements": "- 5+ years backend or full-stack engineering; 1+ year leading engineers (official or tech-lead capacity).\n- Strong system design: APIs, databases, caching, async jobs, observability.\n- Experience with agile rituals; ability to break epics into incremental releases.\n- Comfortable giving feedback and running performance conversations.\n- English B1+ for standups with distributed peers.\n- Empathy for on-call and incident postmortems without blame culture.",
  "job_type": "full_time",
  "level": "lead",
  "required_skills": [
    "People leadership",
    "System design",
    "REST API",
    "SQL",
    "Code review culture",
    "Agile delivery",
    "Incident response",
    "Hiring participation"
  ],
  "preferred_skills": [
    "Python or Go",
    "Kubernetes basics",
    "PostgreSQL",
    "CI/CD",
    "Architecture RFCs",
    "Mentoring",
    "Stakeholder communication"
  ],
  "min_experience": 5,
  "max_experience": 15,
  "salary_min": "5500.00",
  "salary_max": "8000.00",
  "currency": "USD",
  "application_deadline": null
}
```

### 8.4 Product Manager (PM)

```json
{
  "title": "Product Manager — B2B Workflow",
  "company": "Nova Labs",
  "location": "Remote / Tashkent",
  "description": "You own outcomes for a B2B workflow product used by operations teams. You discover problems through interviews and data, write crisp PRDs and user stories, and prioritize ruthlessly against business goals. You work daily with design and engineering; you are the glue between customer pain and shippable increments. Success is measured by adoption, task completion rates, and NPS—not slide decks alone.",
  "requirements": "- 3+ years as PM (or PO in strong product org) for software products.\n- Evidence of shipping features end-to-end with measurable impact.\n- Strong written communication: user stories, acceptance criteria, release notes.\n- Comfort with analytics tools (Amplitude, Mixpanel, or GA4) and SQL basics.\n- Experience with discovery: user interviews, usability tests, hypothesis validation.\n- English B2+; stakeholder management with sales/customer success occasionally.\n- Structured thinker; can say no with data.",
  "job_type": "full_time",
  "level": "mid",
  "required_skills": [
    "Product discovery",
    "Roadmap prioritization",
    "User stories",
    "Analytics",
    "Stakeholder communication",
    "B2B SaaS context",
    "English B2+"
  ],
  "preferred_skills": [
    "SQL",
    "Figma",
    "Jira or Linear",
    "A/B testing",
    "OKRs",
    "API literacy",
    "Go-to-market collaboration",
    "Presentation skills"
  ],
  "min_experience": 3,
  "max_experience": 12,
  "salary_min": "3800.00",
  "salary_max": "5800.00",
  "currency": "USD",
  "application_deadline": null
}
```

**Eslatma:** `salary_*` backend da `Decimal` — qator sifatida yuborish (`"3500.00"`) xavfsiz. Kompaniya nomi, lokatsiya va narxlar — namuna.
