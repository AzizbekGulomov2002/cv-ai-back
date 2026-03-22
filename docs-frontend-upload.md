# CV upload — faqat fayl (OpenAI ajratish)

## Server paketlari (PDF matn)

Agar PDF dan matn chiqmasa, serverda o‘rnating:

```bash
pip install -r requirements.txt
```

`PyMuPDF` va `pypdf` PyPDF2 dan ko‘ra ko‘p CV larni o‘qiydi. **Faqat rasm (skaner)** PDF bo‘lsa — matn bo‘lmaydi; **DOCX** yuboring yoki OCR qiling.

## Qisqa

- **`POST /api/candidates/upload/`** — faqat **PDF/DOCX** yuborish kifoya (`cv_file`, `file` yoki `cv`).
- **Ism/email kiritish shart emas.** Matn lokal ajratiladi, keyin **OpenAI** JSON qaytaradi va barcha asosiy maydonlar shu yerdan to‘ldiriladi.
- **`OPENAI_API_KEY`** bo‘lmasa: heuristik parser (regex + fayl nomi) ishlatiladi, javobda `extraction_source: "heuristic"`.
- Kalit bo‘lsa: `extraction_source: "openai"`.

## `.env`

```env
OPENAI_API_KEY=sk-...
OPENAI_CV_MODEL=gpt-4o-mini
```

## Multipart (minimal)

| Maydon | Majburiy |
|--------|----------|
| `cv_file` **yoki** `file` **yoki** `cv` | Ha |
| `name`, `email`, `phone` | Yo‘q (ixtiyoriy override) |

## JavaScript

```javascript
const fd = new FormData();
fd.append("file", pdfFile, pdfFile.name);

const r = await fetch("https://YOUR-HOST/api/candidates/upload/", {
  method: "POST",
  body: fd,
});
const data = await r.json();
// data.extraction_source === "openai" | "heuristic"
// data.candidate — name, email, skills, ai_profile_json, ...
```

## OpenAI JSON (ichki shakl)

`ai_profile_json` va model maydonlariga map qilinadi:

- `full_name` → `name`
- `email` → `email`
- `phone` → `phone`
- `skills` → `skills` (array)
- `years_of_experience` → `experience_years`
- `education_summary` → `education`
- `professional_summary` — faqat `ai_profile_json` ichida (embedding matniga qo‘shiladi)

Agar ism/email bo‘sh qolsa: fayl nomi / matn taxmini yoki `candidate-{id}@no-email.cv-ai.local`.

## Jarayon (server)

1. Fayl saqlanadi (`media/cvs/...`).
2. **PyPDF2 / python-docx** bilan matn ajratiladi.
3. **OpenAI** chat + `json_object` (yoki fallback) → struktura.
4. **Candidate** yangilanadi + `ai_profile_json` to‘liq saqlanadi.
5. **Embedding**: `extracted_text` + `professional_summary` (OpenAI embedding yoki dummy).

## cURL

```bash
curl -X POST "https://YOUR-HOST/api/candidates/upload/" \
  -F "file=@./resume.pdf"
```
