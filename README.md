# MedVerify Suite

MedVerify Suite is a high-fidelity, autonomous medical document verification and digital forensics platform. It leverages advanced visual neural analysis, OCR extraction, and persistent audit trails to validate the cryptographic and structural integrity of clinical reports, prescriptions, and medical licensing documents.

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

### 1. Backend (Flask + SQLite)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

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

## 🔐 Developer Credentials Cheat Sheet

Use these ready-made credentials to log in and inspect different role capabilities in the system:

| Role | Email | Password | Access Capabilities |
| :--- | :--- | :--- | :--- |
| **System Admin** | `admin@medverify.dev` | `admin123` | Unrestricted full-ledger read/write, Command Center metrics, audit history |
| **Verifier** | `verifier@medverify.dev` | `verifier123` | Access to Analysis Engine (upload), Vault ledger list, individual diagnostic reports |
| **Viewer** | `viewer@medverify.dev` | `viewer123` | Read-only access to ledger list, individual report previews, profile identity terminal |

---

## 🏗 Technology Stack

- **Frontend**: React 19, Vite, Tailwind CSS 4, Framer Motion.
- **Backend**: Flask REST API, SQLite (SQLAlchemy), Celery, Redis.
- **AI/ML**: OCR-Text integrity checks, Error Level Analysis (ELA), Substrate Noise Density mismatch, Copy-Move clone detection, and Typographical Font Consistency checking.
