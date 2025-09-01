import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# Load .env once at import time (works in Flask, scripts, and tests)
dotenv_path = find_dotenv() or Path(__file__).with_name(".env")
load_dotenv(dotenv_path, override=True)


def get_int_env(var_name: str, default: int) -> int:
    """Safely parse an integer from environment variables with fallback."""
    value = os.getenv(var_name, str(default))
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


class Config:
    # App
    APP_VERSION = "1.0.0"
    PORT = get_int_env("PORT", 5000)
    FLASK_ENV = os.getenv("FLASK_ENV", "development")

    # Admin (change in production!)
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "password")

    # n8n legacy webhook (if you still proxy to it)
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

    # RAG / OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    X_API_KEY = os.getenv("X_API_KEY", "changeme")

    # Chunking
    CHUNK_SIZE = get_int_env("CHUNK_SIZE", 1000)
    CHUNK_OVERLAP = get_int_env("CHUNK_OVERLAP", 200)

    # Google Drive ingestion
    GOOGLE_FOLDER_ID = os.getenv("GOOGLE_FOLDER_ID", "")
    GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "")
    POLL_INTERVAL_SECONDS = get_int_env("POLL_INTERVAL_SECONDS", 60)

    # Database (n8n-compatible envs)
    N8N_DB_CONFIG = {
        "dbname": os.getenv("N8N_DB_NAME"),
        "user": os.getenv("N8N_DB_USER"),
        "password": os.getenv("N8N_DB_PASSWORD"),
        "host": os.getenv("N8N_DB_HOST"),
        "port": os.getenv("N8N_DB_PORT", "5432"),
    }

    @staticmethod
    def DATABASE_URL() -> str:
        """Convenience DSN (used by scripts if needed)."""
        c = Config.N8N_DB_CONFIG
        missing = [k for k, v in c.items() if not v]
        if missing:
            raise RuntimeError(f"Missing DB env vars: {', '.join(missing)}")
        return f"postgresql://{c['user']}:{c['password']}@{c['host']}:{c['port']}/{c['dbname']}"
