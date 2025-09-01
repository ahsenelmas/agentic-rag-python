import io, csv
from typing import Dict, Any, List
import pandas as pd
from PyPDF2 import PdfReader

def extract_pdf_text(content: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(content))
        parts = []
        for p in reader.pages:
            parts.append(p.extract_text() or "")
        return "\n".join(parts).strip()
    except Exception:
        return content.decode("utf-8", errors="ignore")

def extract_google_doc_text(content: bytes) -> str:
    return content.decode("utf-8", errors="ignore")

def extract_csv_rows(content: bytes) -> List[Dict[str, Any]]:
    text = content.decode("utf-8", errors="ignore")
    r = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in r]

def extract_xlsx_rows(content: bytes) -> List[Dict[str, Any]]:
    with io.BytesIO(content) as bio:
        df = pd.read_excel(bio)
    return df.to_dict(orient="records")

def keys_schema(rows: List[Dict[str, Any]]) -> List[str]:
    keys = set()
    for r in rows[:50]:
        keys.update(r.keys())
    return sorted(keys)
