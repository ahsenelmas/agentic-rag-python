# Agentic RAG (Drive → Postgres/pgvector → Tools → `/ask`)

A minimal, production-ready RAG service:
- **Ingestion:** Google Drive (Docs/Sheets/PDF) → export → chunk → embed
- **Storage:** Postgres **pgvector** (`documents`, `document_rows`, `document_metadata`)
- **Retrieval:** `match_documents(query_embedding, match_count, filter)`
- **Agent:** OpenAI Chat Completions w/ tool-calling
- **API:** `POST /ask` (header `x-api-key`)

> Medium article: _[link here]_

---

## Quickstart

```bash
python -m venv .venv
# Windows:
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
