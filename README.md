# Agentic RAG (Drive → Postgres/pgvector → Tools → `/ask`)

A minimal, production‑ready RAG service built with **Flask**, **PostgreSQL + pgvector**, and **OpenAI**. Ingest files from **Google Drive**, chunk & embed, store vectors in Postgres, retrieve with a `match_documents` SQL function, and answer via an agent with tool‑calling. Exposes a single `POST /ask` endpoint secured by an `x-api-key`.

<p align="left">
  <a href="#">
    <img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-blue" />
  </a>
  <a href="#">
    <img alt="Flask" src="https://img.shields.io/badge/Flask-API-black" />
  </a>
  <a href="#">
    <img alt="Postgres" src="https://img.shields.io/badge/Postgres-16%2B-336791" />
  </a>
  <a href="#">
    <img alt="pgvector" src="https://img.shields.io/badge/pgvector-required-orange" />
  </a>
  <a href="#">
    <img alt="License" src="https://img.shields.io/badge/License-MIT-green" />
  </a>
</p>

---

* **Medium article:** *https://medium.com/@ahsenelmas1/from-n8n-to-python-building-an-agentic-rag-service-with-flask-postgres-pgvector-and-google-drive-b07bace97b19*

---

## Table of Contents

* [TL;DR (Fastest way to run)](#tldr-fastest-way-to-run)
* [File Structure](#file-structure)
* [Why this layout?](#why-this-layout)
* [.env Template](#env-template)
* [Database Bootstrap (pgvector + tables)](#database-bootstrap-pgvector--tables)
* [Google Drive Ingestion](#google-drive-ingestion)
* [API Usage](#api-usage)
* [Troubleshooting](#troubleshooting)
* [Security](#security)
* [Roadmap](#roadmap)
* [License](#license)

---

## TL;DR (Fastest way to run)

### 1) Create venv + install deps

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Fill `.env` — make sure Postgres is reachable and **pgvector** is enabled

Use the [template](#env-template) below.

or copy the sample to `.env`

```bash
cp .env.sample .env
``` 

### 3) Initialize DB schema (tables + `match_documents`)

```bash
python scripts/init_db.py
```

### 4) (Optional) Ingest Google Drive once

```bash
python -m rag.ingestion.drive_poller --once
python -m scripts.db_checks  # sanity check
```

### 5) Run API

```bash
python app.py
```

### Quick test

**PowerShell one‑liner:**

```powershell
$headers = @{ "x-api-key" = "<X_API_KEY>" }
$body    = '{"message":"hello","sessionId":"demo-1"}'
Invoke-RestMethod -Uri "http://127.0.0.1:5000/ask" -Method Post -Headers $headers -ContentType "application/json" -Body $body
```

**curl:**

```bash
curl -X POST "http://127.0.0.1:5000/ask" \
  -H "x-api-key: <X_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"message":"hello","sessionId":"demo-1"}'
```

---

## File Structure

```
agentic-rag-python/
├─ app.py                  # Flask app exposing /ask
├─ config.py               # Loads .env; central config
├─ db.py                   # psycopg2 connection helper
├─ requirements.txt
├─ .gitignore
├─ rag/
│  ├─ api.py               # Blueprint: /ask (POST) + helpful GET
│  ├─ agent.py             # Chat loop + tool-calling + memory
│  ├─ tools.py             # RAG search, list docs, file contents, SELECT-only SQL
│  ├─ embeddings.py        # OpenAI embeddings client
│  ├─ chunking.py          # Simple character chunker
│  └─ ingestion/
│     ├─ drive_poller.py   # Google Drive → export → chunk → embed → upsert
│     └─ processors.py     # PDF/Doc/CSV/XLSX extractors + schema helper
└─ scripts/
   ├─ init_db.py           # Creates tables + match_documents()
   └─ db_checks.py         # Prints pgvector version + row counts
```

---

## Why this layout?

* Clear separation: **API (Flask)** vs **Agent (LLM logic)** vs **Tools (DB code)** vs **Ingestion (Drive)**.
* Easy to swap embedding providers via `rag/embeddings.py`.
* Ingestion can run separately on a schedule or as a one‑off job.
* SQL tool is **SELECT‑only** for safety.

---

## .env Template

> Do **not** commit `.env` or `google-credentials.json` (they are already in `.gitignore`).

```dotenv
# App
PORT=5000
FLASK_ENV=development
X_API_KEY=choose-a-strong-secret

# OpenAI
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
# OPTIONAL (if you belong to multiple orgs)
# OPENAI_ORG=org_XXXXXX

# Database (pgvector must be enabled in this DB)
N8N_DB_NAME=ragdb
N8N_DB_USER=rag
N8N_DB_PASSWORD=ragpass
N8N_DB_HOST=localhost
N8N_DB_PORT=5432

# Google Drive ingestion
GOOGLE_FOLDER_ID=your-drive-folder-id
GOOGLE_CREDENTIALS_FILE=./google-credentials.json
POLL_INTERVAL_SECONDS=60
```

---

## Database Bootstrap (pgvector + tables)

You need to enable **pgvector** once per database using a privileged role, then run the schema script.

### 1) Enable pgvector (one time)

**Windows PowerShell `psql` one‑liner:**

```powershell
$env:PGPASSWORD = "<ADMIN_PASSWORD>"
psql -h <HOST> -p 5432 -U <ADMIN_USER> -d <DBNAME> -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**Examples**

* Self‑hosted: `-U postgres`
* DigitalOcean Managed: `-U doadmin`
* RDS/Azure: your platform’s admin user

If you see `permission denied to create extension 'vector'`, you’re not using a role with extension privileges.

### 2) Create tables & function

```bash
python scripts/init_db.py
```

**Expected:** ✅ Database initialized (**pgvector** + tables + `match_documents`).

### 3) Sanity check

```bash
python -m scripts.db_checks
```

**You should see something like:**

```
pgvector: ('0.8.0',)
match_documents exists: True
documents: 0
document_rows: 0
metadata sample: []
```

---

## Google Drive Ingestion

* Create a **service account** in Google Cloud → generate JSON key → save as `google-credentials.json` (or set an absolute path in `.env`).
* Share the Drive **folder** with the service account’s `client_email` (viewer/editor). If it’s on a **Shared Drive**, add the service account as a member of that Shared Drive.
* `GOOGLE_FOLDER_ID` is the string after `/folders/` in the Drive URL.

### Run once and exit

```bash
python -m rag.ingestion.drive_poller --once
```

### Continuous watch (Ctrl+C to stop)

```bash
python -m rag.ingestion.drive_poller
```

### Re‑check counts

```bash
python -m scripts.db_checks
```

* Docs/PDFs populate `documents` (chunked text with embeddings).
* Sheets/CSVs populate `document_rows` (tabular JSONB).

**Tip:** put a unique phrase in a test Google Doc (e.g., `purple-raccoon-42`), ingest once, then ask *“Which file mentions purple-raccoon-42?”* to confirm retrieval.

---

## API Usage

**Endpoint**

```
POST /ask
```

**Headers**

```
x-api-key: <X_API_KEY>
Content-Type: application/json
```

**Body**

```json
{ "message": "your question", "sessionId": "chat-123" }
```

**Examples**

*PowerShell*

```powershell
$headers = @{ "x-api-key" = "<X_API_KEY>" }
$body    = '{"message":"What does the onboarding policy say about laptops?","sessionId":"demo-1"}'
Invoke-RestMethod -Uri "http://127.0.0.1:5000/ask" -Method Post -Headers $headers -ContentType "application/json" -Body $body
```

*curl*

```bash
curl -X POST "http://127.0.0.1:5000/ask" \
  -H "x-api-key: <X_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"message":"Summarize the Q3 roadmap from the uploaded doc.","sessionId":"demo-2"}'
```

---

## Troubleshooting

**401 Unauthorized**
`x-api-key` header missing or doesn’t match `X_API_KEY` in `.env`.

**502 with `insufficient_quota`**
Your OpenAI key has no credits/quota. Add billing/use a funded key. If in multiple orgs, set `OPENAI_ORG`.

**Poller says “Found 0 files”**
Wrong `GOOGLE_FOLDER_ID` or the service account lacks access. Share the folder/Shared Drive with `client_email`.

**`FileNotFoundError: ./google-credentials.json`**
Put `google-credentials.json` in repo root or set an absolute path in `.env`:

```
GOOGLE_CREDENTIALS_FILE=C:/Users/you/path/google-credentials.json
```

**pgvector error while bootstrapping**
Run `CREATE EXTENSION vector;` as a privileged role in the target DB.

---

## Security

* Don’t commit `.env` or `google-credentials.json` (gitignored).
* `/ask` requires an API key (`x-api-key`).
* SQL tool is **SELECT‑only**; no writes/DDL allowed.

---

## Roadmap

* Dockerfile + docker‑compose (API + Postgres)
* Unit tests (chunking, tools, agent loop)
* CI (pytest + flake8)
* Admin page for conversations & recent docs

---

## License

**MIT** (or your preferred license). If using MIT, add a `LICENSE` file in the repo root.
