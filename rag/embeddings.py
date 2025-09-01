import requests
from config import Config

def embed_texts(texts):
    headers = {"Authorization": f"Bearer {Config.OPENAI_API_KEY}"}
    r = requests.post("https://api.openai.com/v1/embeddings",
                      headers=headers,
                      json={"model": Config.EMBEDDING_MODEL, "input": texts},
                      timeout=60)
    r.raise_for_status()
    data = r.json()
    return [d["embedding"] for d in data["data"]]
