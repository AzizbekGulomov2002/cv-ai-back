# CV upload — bulut fayl orqali (lokal PDF o‘qish yo‘q)

## Mantiq

1. Frontend faqat **PDF yoki DOCX** yuboradi (`cv_file` / `file` / `cv`).
2. Backend faylni **OpenAI** yoki **Google Gemini** ga yuboradi (sozlamaga qarab).
3. Model **bitta JSON** qaytaradi (ism, email, skills, …) — bu `Candidate` va `ai_profile_json` ga yoziladi.
4. **Lokal PyMuPDF / pypdf** upload yo‘lida ishlatilmaydi.

## Provayderlar

| Rejim | Tavsif |
|-------|--------|
| **OpenAI** | Files API + Responses API + `input_file` + `gpt-4o` (yoki `OPENAI_CV_MODEL`). |
| **Gemini** | `google-generativeai` — fayl yuklash + `generate_content` (sukut: `gemini-2.5-flash`; 404 bo‘lsa zaxira modellar). |
| **`auto`** (sukut) | Avval OpenAI; **429 / quota** bo‘lsa — **Gemini** (agar `GEMINI_API_KEY` bo‘lsa). |

`CV_EXTRACT_PROVIDER=openai` yoki `gemini` — faqat bitta provayder.

## Talablar

- Kamida bittasi: **`OPENAI_API_KEY`** yoki **`GEMINI_API_KEY`** (yoki `GOOGLE_API_KEY`).
- `pip install -r requirements.txt` — `openai>=1.70.0`, `google-generativeai`.

### Gemini kaliti (vaqtincha bepul tier)

[Google AI Studio](https://aistudio.google.com/apikey) dan API key oling va `.env` ga qo‘shing.

## `.env`

```env
OPENAI_API_KEY=sk-...
OPENAI_CV_MODEL=gpt-4o

# Fallback / faqat Gemini
GEMINI_API_KEY=...
GEMINI_CV_MODEL=gemini-2.5-flash
CV_EXTRACT_PROVIDER=auto
```

`gpt-4o-mini` ham sinab ko‘rish mumkin; PDF uchun `gpt-4o` ishonchliroq.

## Frontend

```javascript
const fd = new FormData();
fd.append("file", pdfFile, pdfFile.name);
await fetch("/api/candidates/upload/", { method: "POST", body: fd });
```

## Muvaffaqiyatli javob (201)

Asosiy maydonlar:

| Maydon | Tavsif |
|--------|--------|
| `extracted_profile` | LLM qaytargan **to‘liq** JSON (`source`, `gemini_model` / `openai_model` bilan) — `candidate.ai_profile_json` bilan bir xil |
| `cv_parsed` | Faqat CV maydonlari: `full_name`, `email`, `phone`, `skills`, `years_of_experience`, `education_summary`, `professional_summary`, `embedding_text` |
| `extraction` | `source`, `openai_model` yoki `gemini_model` |
| `extracted_text` | DB ga yozilgan embedding / qidiruv matni |
| `candidate` | `CandidateSerializer` — shu jumladan `skills`, `education`, `experience_years`, `ai_profile_json` |

## Lokal test (terminal)

```bash
cd ai_cv_system
export OPENAI_API_KEY=sk-...
export GEMINI_API_KEY=...   # ixtiyoriy — quota tugaganda ishlatiladi
python scripts/test_cv_openai_file.py "/path/to/AzizbekGulomov CV.pdf"
```

JSON chiqsa — pipeline ishlayapti. `null` bo‘lsa — loglarni tekshiring.

---

## Qisqa

| Qadam | Nima |
|-------|------|
| 1 | `POST` multipart, fayl saqlanadi |
| 2 | OpenAI yoki Gemini fayl + model |
| 3 | JSON parse → `Candidate` |
| 4 | `embedding_text` / summary bo‘yicha embedding |
