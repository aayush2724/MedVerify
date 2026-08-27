# MedVerify Suite

MedVerify Suite is a two-module medical safety platform built on one backbone
(shared auth, RBAC, audit log and admin console):

| Module | Audience | What it does |
| :--- | :--- | :--- |
| **1 — Document Forensics** | Verifiers, hospitals, auditors | Checks whether an uploaded medical certificate or report is authentic or tampered, using OCR text integrity plus image forensics. |
| **2 — Medication Safety Check** | Consumers / patients | Checks a personal medication list for duplicated active ingredients and combined daily totals against published FDA label limits. |

---

## ⚕️ Module 2 — Medication Safety Check

### What it is, and deliberately is not

Module 2 is an **informational tool for consumers checking their own
medications**. It is explicitly *not* clinical decision support, and the
architecture enforces that rather than merely disclaiming it:

* **No ML decides safety.** Findings come from a named, readable rule engine
  (`app/services/medication_safety_service.py`) over public data. Machine
  learning is used only for OCR extraction, never for a safety verdict.
* **Every finding is sourced.** `MedicationSafetyService._finding()` raises if a
  finding is built without a citation or the consult-a-professional caveat, so
  an uncited claim cannot reach a user even if a future rule forgets.
* **The caveat travels with the result**, inside each finding — not only in page
  furniture that a screenshot can crop away.
* **Gaps are stated, never silent.** An unmatched product or an ingredient with
  no limit on file produces an explicit "could not be checked" finding, because
  a quiet result must never read as a clean bill of health.

### Phase 1 (implemented)

1. **Duplicate active ingredient** (`RULE-DUP-01`) — the same ingredient across
   two or more products. Salt forms are normalised, so
   *diphenhydramine hydrochloride* collides with *diphenhydramine*.
2. **Cumulative daily dose** (`RULE-DOSE-01`) — combined daily total vs. the
   labeled maximum. `high` at or above the limit, `moderate` from 80%.
3. **Coverage gaps** (`RULE-GAP-01/02/03`) — unmatched products, non-milligram
   strengths, and ingredients with no published limit on file.

### Phase 2 (next) — drug–drug interactions

⚠️ **NLM retired the RxNav Interaction API in January 2024** (it now returns
404), so Phase 2 must source interactions from the openFDA label
`drug_interactions` section rather than RxNav. The caching and citation
plumbing in `drug_data_service.py` already supports this.

### Phase 3 (later) — combined pipeline

OCR a prescription once, then run it through *both* the forensics module and
the safety module. The groundwork exists: `POST /api/medications/scan` already
shares Module 1's `OCREngine` and `DocumentProcessor`.

### Data sources

| Source | Used for | Cached in |
| :--- | :--- | :--- |
| **RxNorm / RxNav** (NLM) | Product search, active-ingredient breakdown with per-unit strength (SCDC concepts) | `drug_concepts`, `drug_ingredients`, `external_api_cache` |
| **openFDA drug label** | Verbatim label text cited alongside a dose finding | `external_api_cache` |
| **Curated limit table** | Numeric maximum daily doses, transcribed from FDA OTC monographs | `ingredient_limits` (seeded from `app/data/ingredient_limits.py`) |

Maximum daily doses are a **hand-curated, reviewable table**, not a scraped
value: openFDA publishes dosing only as free-text prose, and parsing a number
out of it would silently produce wrong maxima. Each row names its monograph.
Edit `app/data/ingredient_limits.py` and restart to publish a corrected limit.

### API

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `GET` | `/api/medications/search?q=` | RxNorm autocomplete |
| `GET` | `/api/medications/concept/<rxcui>` | Ingredient breakdown for one product |
| `GET` | `/api/medications` | The caller's medication list |
| `POST` | `/api/medications` | Add (by `rxcui`, or free-text `display_name`) |
| `PUT` | `/api/medications/<id>` | Update dose / schedule |
| `DELETE` | `/api/medications/<id>` | Soft-remove (keeps past checks resolvable) |
| `POST` | `/api/medications/safety-check` | Run the rule engine |
| `GET` | `/api/medications/safety-checks` | Past checks |
| `GET` | `/api/medications/safety-checks/<id>` | One stored result |
| `POST` | `/api/medications/scan` | OCR a package photo → candidate products |

All routes are scoped to the calling user. Unlike Module 1 there is **no admin
override** — a medication list is personal data.

### Screens

`/medications` (My Medications) · `/medications/add` (search + package scan) ·
`/medications/report` (results, colour-coded to match Module 1's Tamper Signal /
Content Audit Check pattern).

### Demo data

```bash
MEDVERIFY_DEMO_PASSWORD='...' python seeds/seed_medication_demo.py
```

Seeds `patient@medverify.dev` with three ordinary products — Tylenol, a
night-time acetaminophen/diphenhydramine tablet, and Percocet — each at a normal
label dose. No single line looks wrong; together they reach **4,250 mg of
acetaminophen a day against a 4,000 mg labeled maximum**, and only one of the
three has "acetaminophen" in the name a patient would read.

---

## 🚀 Key Features

### 1. Unification to MedVerify Branding
* Re-branded the entire stack to **MedVerify** file-wide.
* Cleaned up legacy domains and database defaults, replacing them with standard `@medverify.dev` configurations.

### 2. High-Fidelity Certificate Document Viewer
* **Persistent Retention**: Uploaded PDF and image certificates are securely and conditionally stored on disk upon successful verification pipeline runs.
* **Dual Auth Token Serving**: Includes a secure media serving endpoint `/api/certificates/<record_id>/file` supporting standard `Authorization` headers and native browser direct query parameters (`?token=...`).
* **Interactive Lightbox Modal**: Integrated full-screen glassmorphic media players with PDF frame embeds, centered image containment, download anchors, and direct diagnostic hooks inside the Verification Vault and Report canvases.
* **Dynamic Placeholder Generator**: If a record's physical file is missing from disk (e.g. pre-seeded mock ledger rows), the backend dynamically renders a premium certificate image matching the database record's status, filename, UUID, and submission timestamp. If the format ends in `.pdf`, it uses Pillow's native PDF encoder to compile a valid PDF on the fly, preventing browser PDF engine crashes.

### 3. Verification Signals & Anomalies Translation
* Added a dynamic reasons mapping system in the frontend to translate technical developer jargon (such as ELA score, noise inconsistency, and clone detection flags) into professional, highly readable patient-centric/auditor-centric statements.
* Color-coded and categorized signals: active tampering indicators are flagged as high-severity red **Tamper Signals**, while missing clinical parameters are designated as informational blue/purple **Content Audit Checks**.

### 4. Interactive Profile settings
* Added an **Identity Terminal (`/profile` - `Profile.jsx`)** for real-time user profile updates (Full Name, Email Address, and Custom Avatars).
* Created a corresponding PUT `/api/auth/update-profile` endpoint in the Flask backend that alters SQLite records. Changes automatically propagate reactively across all sidebar footer layouts.

### 5. Administrative DB & File cleanup
* Created a dedicated cleanup tool `wipe_data.py` inside the backend directory. Running it securely wipes all `verification_records` and `audit_logs` database entries, and cleans up the physical files in the `uploads/` directory, resetting the stack to a pristine environment.

---

## 🛠 Manual Development Setup

### 1. Backend (Flask + PostgreSQL)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm    # hospital/doctor NER for Module 1

# Start PostgreSQL (or point DATABASE_URL at an existing instance)
docker compose up -d db redis

export DATABASE_URL=postgresql://medverify:change_me@localhost:5432/medverify
alembic upgrade head                        # creates both modules' schema
python run.py
```

SQLite still works for a quick look (`DATABASE_URL=sqlite:///./medverify_dev.db`),
but PostgreSQL is the supported database: Module 2 carries materially higher
read/write volume and stores cached drug data as JSONB.

### 2. Seeding & Admin Tools (SQLite)
To populate the database with default roles, mock documents, and logs:
```bash
python seeds/seed_dev_data.py
```

To wipe all data cleanly:
```bash
python wipe_data.py
```

### 3. Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```

* **Frontend URL**: `http://localhost:5173`
* **Backend API (Proxied)**: `http://localhost:5000`

---

## 🔐 Developer Accounts

Set these optional environment variables before starting or seeding the app to create local development users:

| Role | Email | Password Environment Variable | Access Capabilities |
| :--- | :--- | :--- | :--- |
| **System Admin** | `admin@medverify.dev` | `MEDVERIFY_SEED_ADMIN_PASSWORD` | Unrestricted full-ledger read/write, Command Center metrics, audit history |
| **Verifier** | `verifier@medverify.dev` | `MEDVERIFY_SEED_VERIFIER_PASSWORD` | Access to Analysis Engine (upload), Vault ledger list, individual diagnostic reports |
| **Viewer** | `viewer@medverify.dev` | `MEDVERIFY_SEED_VIEWER_PASSWORD` | Read-only access to ledger list, individual report previews, profile identity terminal |

---

## 🏗 Technology Stack

- **Frontend**: React 19, Vite, Tailwind CSS 4, Framer Motion.
- **Backend**: Flask REST API, **PostgreSQL** (SQLAlchemy + Alembic), Celery, Redis.
- **Module 1 AI/ML**: OCR text integrity, Error Level Analysis (ELA), substrate
  noise density, copy-move clone detection, font consistency.
- **Module 2**: transparent rule engine over RxNorm + openFDA. No model.

### OCR engine chain

`Google Vision (opt-in) → Tesseract → RapidOCR (ONNX)`. RapidOCR is
pip-installable and needs no system binary, so the pipeline works on hosts
without Tesseract. `OCREngine.last_engine` records which engine produced the
text.

### ⚠️ Known limitation — Module 1 image forensics are uncalibrated

The visual forensic signals have **not been validated against a labelled
dataset**, and `ml/models/` ships empty, so `CertificateClassifier` always runs
its rule-based fallback. Measured on a clean render, a scan-simulated copy and a
deliberately spliced copy of the same certificate, the substrate-noise metric
returns 2.41 / 2.41 / 2.37 — no separation. It is therefore recorded as a
feature and flagged *advisory only*; it no longer forces a `FAKE` verdict.

Treat Module 1's verdict as a triage aid pending a labelled evaluation set, and
do not present a confidence percentage to a client as a validated accuracy
figure.
