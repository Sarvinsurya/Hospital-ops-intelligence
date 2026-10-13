"""SQLite connection helpers for the warehouse."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from app.core.config import settings


def get_connection() -> sqlite3.Connection:
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


@contextmanager
def db_cursor():
    conn = get_connection()
    try:
        yield conn.cursor()
        conn.commit()
    finally:
        conn.close()


def query_df(sql: str, params: tuple | dict | None = None) -> pd.DataFrame:
    """Run a read query and return a DataFrame."""
    conn = get_connection()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def db_exists() -> bool:
    p = Path(settings.db_path)
    if not p.exists():
        return False
    try:
        df = query_df(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='fact_admissions'"
        )
        return not df.empty
    except Exception:
        return False
