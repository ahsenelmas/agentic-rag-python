import os
import psycopg2
from contextlib import contextmanager
from dotenv import load_dotenv, find_dotenv

REQUIRED_VARS = [
    "N8N_DB_NAME",
    "N8N_DB_USER",
    "N8N_DB_PASSWORD",
    "N8N_DB_HOST",
    "N8N_DB_PORT",
]


def _db_config():
    load_dotenv(find_dotenv(), override=False)
    missing = [k for k in REQUIRED_VARS if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing DB env vars: {', '.join(missing)}")
    return {
        "dbname": os.getenv("N8N_DB_NAME"),
        "user": os.getenv("N8N_DB_USER"),
        "password": os.getenv("N8N_DB_PASSWORD"),
        "host": os.getenv("N8N_DB_HOST"),
        "port": os.getenv("N8N_DB_PORT"),
    }


@contextmanager
def get_db_connection():
    """
    Yield a psycopg2 connection.

    On success: COMMIT.
    On psycopg2 errors: ROLLBACK.
    The connection is always closed.
    """
    conn = None
    try:
        try:
            conn = psycopg2.connect(**_db_config())
        except psycopg2.Error as e:
            # Split long string for flake8 line-length compliance
            raise RuntimeError(
                "Failed to connect to DB. "
                "Check credentials/network/env vars. "
                f"Original error: {e}"
            ) from e

        yield conn
        conn.commit()
    except psycopg2.Error:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
