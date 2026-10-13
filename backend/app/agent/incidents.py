"""
Incident log — persists every agent investigation as a timestamped incident.

Backed by a dedicated SQLite table in the warehouse so the UI can show an
investigation history ("war room" feed). Stores the trigger, the agent's answer,
the tools used, and the full reasoning trace for explainability.
"""
from __future__ import annotations

import json
from datetime import datetime

from app.core.database import get_connection


def _ensure_table():
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                trigger_type TEXT,
                severity TEXT,
                title TEXT,
                query TEXT,
                answer TEXT,
                tools_used TEXT,
                trace TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def log_incident(title: str, query: str, investigation: dict,
                 trigger_type: str = "manual", severity: str = "info") -> int:
    _ensure_table()
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO incidents
                (created_at, trigger_type, severity, title, query, answer, tools_used, trace)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                trigger_type,
                severity,
                title,
                query,
                investigation.get("answer", ""),
                json.dumps(investigation.get("tools_used", [])),
                json.dumps(investigation.get("trace", []), default=str),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def list_incidents(limit: int = 50) -> list[dict]:
    _ensure_table()
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM incidents ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["tools_used"] = json.loads(d.get("tools_used") or "[]")
            d["trace"] = json.loads(d.get("trace") or "[]")
            out.append(d)
        return out
    finally:
        conn.close()


def get_incident(incident_id: int) -> dict | None:
    _ensure_table()
    conn = get_connection()
    try:
        r = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["tools_used"] = json.loads(d.get("tools_used") or "[]")
        d["trace"] = json.loads(d.get("trace") or "[]")
        return d
    finally:
        conn.close()
