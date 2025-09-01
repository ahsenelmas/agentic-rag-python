from typing import Dict, Any, List
from db import get_db_connection
from .embeddings import embed_texts

TOP_K = 6

def rag_search(query: str) -> List[Dict[str, Any]]:
    vec = embed_texts([query])[0]
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM match_documents(%s, %s, '{}'::jsonb)", (vec, TOP_K))
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

def tool_list_documents():
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, title, url, created_at, schema FROM document_metadata ORDER BY created_at DESC")
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

def tool_get_file_contents(file_id: str) -> str:
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT string_agg(content, ' ') AS document_text
            FROM documents
            WHERE metadata->>'doc_id' = %s
            GROUP BY metadata->>'doc_id'
        """, (file_id,))
        row = cur.fetchone()
        return row[0] if row else ""

def tool_query_document_rows(sql_query: str):
    sql = sql_query.strip().rstrip(";")
    if not sql.lower().startswith("select"):
        raise ValueError("Only SELECT queries are allowed.")
    if "document_rows" not in sql.lower():
        raise ValueError("Query must target document_rows.")
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(sql)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
