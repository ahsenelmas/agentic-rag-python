import io, json, time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from db import get_db_connection
from config import Config
from .processors import (
    extract_pdf_text, extract_google_doc_text,
    extract_csv_rows, extract_xlsx_rows, keys_schema
)
from rag.chunking import chunk_text
from rag.embeddings import embed_texts

def _drive():
    creds = service_account.Credentials.from_service_account_file(
        Config.GOOGLE_CREDENTIALS_FILE,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    return build("drive", "v3", credentials=creds)

def _download(service, file_id):
    req = service.files().get_media(fileId=file_id)
    bio = io.BytesIO()
    dl = MediaIoBaseDownload(bio, req)
    done = False
    while not done:
        _, done = dl.next_chunk()
    bio.seek(0)
    return bio.read()

def _export(service, file_id, mime):
    req = service.files().export_media(fileId=file_id, mimeType=mime)
    bio = io.BytesIO()
    dl = MediaIoBaseDownload(bio, req)
    done = False
    while not done:
        _, done = dl.next_chunk()
    bio.seek(0)
    return bio.read()

def process_file(service, f):
    file_id, mime, title = f["id"], f["mimeType"], f["name"]
    url = f.get("webViewLink")

    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM documents WHERE metadata->>'doc_id'=%s", (file_id,))
        cur.execute("DELETE FROM document_rows WHERE dataset_id=%s", (file_id,))
        cur.execute("""
            INSERT INTO document_metadata (id, title, url)
            VALUES (%s,%s,%s)
            ON CONFLICT (id) DO UPDATE SET title=EXCLUDED.title, url=EXCLUDED.url
        """, (file_id, title, url))
        conn.commit()

    if mime == "application/pdf":
        text = extract_pdf_text(_download(service, file_id))
        chunks = chunk_text(text, Config.CHUNK_SIZE, Config.CHUNK_OVERLAP)
        embs = embed_texts(chunks) if chunks else []
        with get_db_connection() as conn, conn.cursor() as cur:
            for i,(c,e) in enumerate(zip(chunks, embs)):
                cur.execute("INSERT INTO documents (content, metadata, embedding) VALUES (%s,%s,%s)",
                            (c, json.dumps({"doc_id":file_id,"file_title":title,"chunk_index":i}), e))
            conn.commit()

    elif mime == "application/vnd.google-apps.document":
        text = extract_google_doc_text(_export(service, file_id, "text/plain"))
        chunks = chunk_text(text, Config.CHUNK_SIZE, Config.CHUNK_OVERLAP)
        embs = embed_texts(chunks) if chunks else []
        with get_db_connection() as conn, conn.cursor() as cur:
            for i,(c,e) in enumerate(zip(chunks, embs)):
                cur.execute("INSERT INTO documents (content, metadata, embedding) VALUES (%s,%s,%s)",
                            (c, json.dumps({"doc_id":file_id,"file_title":title,"chunk_index":i}), e))
            conn.commit()

    elif mime == "application/vnd.google-apps.spreadsheet":
        rows = extract_csv_rows(_export(service, file_id, "text/csv"))
        if rows:
            with get_db_connection() as conn, conn.cursor() as cur:
                for r in rows:
                    cur.execute("INSERT INTO document_rows (dataset_id, row_data) VALUES (%s,%s)", (file_id, json.dumps(r)))
                cur.execute("UPDATE document_metadata SET schema=%s WHERE id=%s", (json.dumps(keys_schema(rows)), file_id))
                conn.commit()

def main(once: bool = False):
    service = _drive()
    q = f"'{Config.GOOGLE_FOLDER_ID}' in parents and (mimeType != 'application/vnd.google-apps.folder')"
    while True:
        res = service.files().list(q=q, spaces="drive",
                                   fields="files(id,name,mimeType,webViewLink,modifiedTime)",
                                   includeItemsFromAllDrives=True, supportsAllDrives=True).execute()
        files = res.get("files", [])
        print(f"Found {len(files)} files.")
        for f in files:
            try:
                process_file(service, f)
                print(f"Processed: {f['name']} ({f['id']})")
            except Exception as e:
                print("Error processing", f.get("name"), e)
        if once:
            break
        print(f"Sleeping {Config.POLL_INTERVAL_SECONDS}s... (Ctrl+C to stop)")
        time.sleep(Config.POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    main(once=args.once)
