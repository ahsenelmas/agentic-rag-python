import os, sys
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

DB_NAME = os.getenv("N8N_DB_NAME")
DB_USER = os.getenv("N8N_DB_USER")
DB_PASS = os.getenv("N8N_DB_PASSWORD")
DB_HOST = os.getenv("N8N_DB_HOST")
DB_PORT = os.getenv("N8N_DB_PORT", "5432")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

DDL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
  id BIGSERIAL PRIMARY KEY,
  content   TEXT,
  metadata  JSONB,
  embedding VECTOR(1536)
);

CREATE OR REPLACE FUNCTION match_documents(
  query_embedding VECTOR(1536),
  match_count    INT,
  filter         JSONB DEFAULT '{}'::jsonb
) RETURNS TABLE (id BIGINT, content TEXT, metadata JSONB, similarity DOUBLE PRECISION)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT d.id, d.content, d.metadata,
         1 - (d.embedding <=> query_embedding) AS similarity
  FROM documents d
  WHERE (filter IS NULL OR filter = '{}'::jsonb OR d.metadata @> filter)
  ORDER BY d.embedding <=> query_embedding
  LIMIT match_count;
END; $$;

CREATE TABLE IF NOT EXISTS document_metadata (
  id TEXT PRIMARY KEY,
  title TEXT,
  url TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  schema TEXT
);

CREATE TABLE IF NOT EXISTS document_rows (
  id SERIAL PRIMARY KEY,
  dataset_id TEXT REFERENCES document_metadata(id),
  row_data JSONB
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id BIGSERIAL PRIMARY KEY,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user','assistant','system','tool')),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
"""

with psycopg2.connect(DATABASE_URL) as conn:
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(DDL)

print("✅ Database initialized (pgvector + tables + match_documents).")
