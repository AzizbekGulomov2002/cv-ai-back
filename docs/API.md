# AI CV System — REST API (bitta hujjat)

**Base URL (lokal):** `http://127.0.0.1:8000`  
**Prefix:** `/api/`

Sukut: `API_REQUIRE_AUTH=false` — ko‘p endpointlar token talab qilmaydi. Production da `API_REQUIRE_AUTH=true`.

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

### 3.3 Boshqa

| Method | Path |
|--------|------|
| GET | `/api/candidates/<id>/` |
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
