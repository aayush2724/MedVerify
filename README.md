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

### Phase 2 (implemented) — drug–drug interactions

**NLM retired the RxNav Interaction API in January 2024**, so there is no longer
a public endpoint that answers "do A and B interact?". What is still published
is the label text itself, so `RULE-INT-01` reads each ingredient's openFDA label
and reports, verbatim, where that label warns about something else on the list.

The claim it makes is *"this label says X"* — checkable — rather than *"these
drugs interact"*, which would be the clinical judgement this module refuses to
make. Concretely:

* **Both match strengths are distinguished.** `ingredient` means drug A's label
  names drug B outright. `class` means the label named a class B belongs to
  ("other NSAIDs", "CNS depressants"), resolved through the curated, reviewable
  table in `app/data/interaction_classes.py`. The finding says which one fired.
* **Severity comes from the label's own wording, and says so.** A sentence
  carrying do-not-combine language ("do not take", "is contraindicated") raises
  the finding to `high`; anything else is `moderate`. openFDA publishes no
  severity grade, and the finding states that its ranking is not a clinical one.
* **The matched sentence is quoted**, with the label section it came from, so
  the escalation is visible rather than a hidden score.
* **Co-formulation is not an interaction.** A combination product reciting its
  own contents ("each caplet contains…") is skipped — that is `RULE-DUP-01`'s
  territory.
* **`RULE-GAP-04/05`** name every ingredient whose label could not be read, or
  that fell past the per-check scan cap.

### Phase 3 (implemented) — combined pipeline

`POST /api/pipeline/analyse` runs one upload through *both* modules in a single
pass. `VerificationService.verify()` already preprocesses the image and stores
the OCR text, so the safety half reads that same text — the OCR happens once.

The medication list here was read off a photograph and confirmed by nobody,
which is a materially weaker input than a hand-entered list, and the design
refuses to hide the difference:

* Results are stamped `source: "prescription"` with a `provenance` block naming
  the document and recording `confirmed_by_user: false`.
* Each detected line reports whether its dosing was `parsed` from the page or
  `assumed`. A frequency the page never stated is never shown as though it did.
* Sig notation is read where present — `1-0-1`, `BD`, `TDS`, `q8h`, `2 tablets
  twice daily`. Leading item numbers are stripped, because OCR drops the
  punctuation and "4. Tab. Aspirin" otherwise reads as four tablets.
* An unresolvable line is passed to the rule engine anyway and reported through
  `RULE-GAP-01`, rather than dropped — a shorter list looks cleaner than it is.
* When RxNorm only offers a combination product for a line naming one drug, the
  extra ingredients are named explicitly, because the rules would otherwise
  report on a drug the prescription never mentioned.
* **Nothing is written to the user's saved medication list.** An OCR guess must
  not quietly become the list every future check runs against.

Screen: `/prescription-check`.

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

**Phase 3 — combined pipeline** (`/api/pipeline`)

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `POST` | `/api/pipeline/analyse` | One upload → forensics verdict + medication safety check |
| `GET` | `/api/pipeline/<record_id>` | Re-read a stored combined report |

**Health** (`/api/health`) — `/api/health` is liveness, `/api/health/ready`
checks PostgreSQL and Redis and returns 503 when either is down.

All routes are scoped to the calling user. Unlike Module 1 there is **no admin
override** — a medication list is personal data.

### Screens

`/medications` (My Medications) · `/medications/add` (search + package scan) ·
`/medications/report` (results, colour-coded to match Module 1's Tamper Signal /
Content Audit Check pattern) · `/prescription-check` (Phase 3: one document
through both modules).

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

## 🚢 Deployment

**[DEPLOYMENT.md](DEPLOYMENT.md)** is the full guide. The short version:

```bash
cp .env.production.example .env     # then fill in the three secrets it names
docker compose -f docker-compose.prod.yml up -d --build
curl localhost/api/health/ready
```

nginx serves the built SPA and reverse-proxies `/api` to the backend, so the
browser sees one origin and CORS is never involved. PostgreSQL and Redis publish
no ports. Migrations run from the backend entrypoint, and `create_all()` is
disabled in production so Alembic is the schema's only owner. Add `--profile
tls` with a `DOMAIN` set to have Caddy obtain certificates automatically.

Two things worth knowing before you build your own image:

* **The backend builds from the repository root**, not from `backend/` —
  `app/errors.py` imports the root-level `shared/` package, which a
  backend-scoped context cannot see.
* **`libgl1` is required** even though `requirements.txt` asks for
  `opencv-python-headless`: `rapidocr-onnxruntime` depends on the full
  `opencv-python`, and that build wins the `cv2` import.

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

### 3. Tests

```bash
cd backend && python -m pytest tests/ -q      # 101 tests, fully offline
```

The suite stubs RxNorm and openFDA at the service boundary, so it is
deterministic and never depends on either API being reachable.

### 4. Frontend (React + Vite)
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
