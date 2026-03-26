# AI CV System — Product Workflow and Decision Guide

This document explains the system in business terms: the workflow, structure, filters, common problems, and practical solutions. It is intentionally **not API-based**.

---

## 1) What this system does

The AI CV System helps recruiters process many CVs quickly and consistently.

It does three core jobs:

1. **Transforms CV files into structured candidate profiles** (skills, experience, education, summary).
2. **Compares each candidate against a target job** using explainable dimensions.
3. **Generates ranked candidate lists** so HR can review faster and make final human decisions.

The platform is a **decision-support tool**, not an auto-hiring engine.

---

## 2) End-to-end workflow

### Step 1: Define the job clearly

Recruiter creates a job profile with:
- clear role description
- required skills
- preferred skills
- minimum experience

Why this matters: ranking quality is heavily dependent on how clear and specific the job data is.

### Step 2: Upload candidate CVs

CV files are ingested and parsed by AI extraction logic.
The system stores structured fields such as:
- candidate identity/contact
- extracted skills
- years of experience
- education summary
- professional summary

### Step 3: Build match intelligence

The system generates text embeddings for job and candidate content.
Then it computes multiple match dimensions and a final composite score.

### Step 4: Produce ranking list

Candidates are sorted by composite score (highest first) and assigned rank positions.
Each row includes explainability details so HR can understand *why* someone ranked higher or lower.

### Step 5: Human review and decision

Recruiters review ranked candidates, check breakdowns, and apply human judgment:
- shortlist
- accept
- reject

Human decisions remain the final authority.

---

## 3) How AI is involved (clear explanation)

AI is involved in two places:

### A) CV understanding
- AI extracts structured information from raw CV files.
- It normalizes text into machine-usable fields.
- This reduces manual data entry and speeds up screening.

### B) Matching and ranking
- Embeddings measure semantic closeness between candidate and job context.
- Rule-based dimensions evaluate skill coverage, experience fit, and education signals.
- A weighted composite score determines ranking order.

Important: AI supports prioritization; it does **not** make irreversible hiring decisions.

---

## 4) Ranking logic and dimensions

Ranking uses a weighted, explainable model.
The final score is based on these dimensions:

- **Semantic alignment**: how closely candidate and job texts match in meaning.
- **Required skills coverage**: how many required skills are present.
- **Preferred skills coverage**: extra desirables matched.
- **Experience fit**: candidate years vs minimum job requirement.
- **Education signals**: education relevance heuristic from extracted text.

### What rank means
- Rank #1 = highest composite score in that session.
- Lower rank does not always mean “bad candidate”; it means “less aligned to this specific job definition.”

---

## 5) Filter strategy (for better shortlist quality)

Use filters to reduce noise before final review.

Recommended filter groups:

- **Job scope filters**
  - target role
  - level (junior/mid/senior)
  - location or timezone fit

- **Candidate capability filters**
  - minimum score threshold
  - required skill must-have set
  - experience range
  - language proficiency

- **Process filters**
  - human decision status (pending/shortlisted/rejected)
  - reviewed vs not reviewed
  - latest session vs historical session

Best practice:
- start broad,
- apply must-have filters,
- then tighten with score and review-status filters.

---

## 6) System structure (business view)

### Candidate domain
Stores uploaded CV file, extracted profile, and historical match/ranking results.

### Job domain
Stores hiring requirements and target profile definitions used for matching.

### Ranking domain
Runs scoring sessions and keeps ranking history, explanations, and human overrides.

### AI services layer
Handles CV extraction, embeddings, scoring dimensions, and explanation text generation.

### Audit and governance layer
Tracks actions and supports compliance-style traceability.

---

## 7) Common problems and practical solutions

### Problem 1: Results feel inaccurate
**Cause:** Job requirements are too generic or incomplete.  
**Solution:** Improve job quality first (clear required skills, realistic experience bar, precise role scope).

### Problem 2: Strong candidates ranked lower than expected
**Cause:** Skill naming mismatch (e.g., synonyms, abbreviation differences).  
**Solution:** Standardize skill taxonomy and normalize skill aliases.

### Problem 3: Similar scores across many candidates
**Cause:** Weak signal in job text or non-production embedding setup.  
**Solution:** Use richer job descriptions and production embedding configuration.

### Problem 4: Recruiters do not trust AI output
**Cause:** Black-box feeling.  
**Solution:** Expose dimension-level explanations and require human review gates before final decisions.

### Problem 5: Screening takes too long despite automation
**Cause:** UI does not support quick comparison and filtering.  
**Solution:** Build workflow-first dashboard features (see next section).

---

## 8) Dashboard improvements (easier and more attractive)

To make implementation easier for recruiters and visually stronger, focus on:

### A) Workflow-first layout
- Left panel: filter controls
- Center: ranked table/cards
- Right drawer: candidate detail + dimension breakdown

### B) Decision acceleration widgets
- quick action buttons: shortlist / reject / hold
- bulk actions for selected candidates
- saved filter presets per job

### C) Explainability UI
- score gauge + dimension bars
- matched vs missing skills chips
- confidence and fairness notices in plain language

### D) Clarity and trust
- show “AI suggestion” badge, not “AI decision”
- always display “Human final decision required”

### E) Visual polish
- consistent spacing, 8px grid
- high-contrast status colors
- sortable columns and sticky table header
- lightweight animations only where they improve comprehension

---

## 9) Recommended operating model

1. Hiring manager defines job profile quality checklist.
2. Recruiter uploads CVs and runs initial ranking.
3. Recruiter applies filters and prepares shortlist.
4. Hiring manager reviews top candidates with dimension breakdown.
5. Team records human decisions and feedback.
6. Process owner reviews outcomes and refines job/skill definitions.

This creates a repeatable loop where model usefulness improves through better input quality and structured review behavior.

---

## 10) Key message for stakeholders

The AI CV System improves speed, consistency, and transparency in CV screening.
It is most effective when:
- job definitions are clear,
- filters are used intentionally,
- explanations are visible,
- and humans stay in control of final hiring outcomes.
