# scripts/db_checks.py
from db import get_db_connection

with get_db_connection() as conn, conn.cursor() as cur:
    # Is pgvector enabled?
    cur.execute("SELECT extversion FROM pg_extension WHERE extname='vector'")
    print("pgvector:", cur.fetchone())

    # Does match_documents exist?
    cur.execute("SELECT proname FROM pg_proc WHERE proname='match_documents'")
    print("match_documents exists:", bool(cur.fetchall()))

    # Counts
    cur.execute("SELECT count(*) FROM documents")
    print("documents:", cur.fetchone()[0])

    cur.execute("SELECT count(*) FROM document_rows")
    print("document_rows:", cur.fetchone()[0])

    cur.execute("SELECT id, title FROM document_metadata ORDER BY created_at DESC LIMIT 5")
    print("metadata sample:", cur.fetchall())
