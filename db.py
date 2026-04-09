"""SQLite schema, connection helpers, and thin repository functions."""
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterable

import config

_LOCAL = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
  id INTEGER PRIMARY KEY,
  profile_url TEXT UNIQUE NOT NULL,
  first_name TEXT, last_name TEXT, full_name TEXT,
  title TEXT, company TEXT, location TEXT,
  seniority TEXT, department TEXT,
  years_in_role REAL, years_at_company REAL,
  shared_connections_json TEXT,
  shared_experiences_json TEXT,
  teamlink_connection TEXT,
  buying_signal TEXT,
  recent_activity_json TEXT,
  account_company_size TEXT,
  account_industry TEXT,
  account_technologies_json TEXT,
  is_connected INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS sequences (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  segment_role_keywords TEXT,
  segment_seniority TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prompt_templates (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  target_role_keywords TEXT,
  target_seniority TEXT,
  message_angle TEXT NOT NULL,
  delivery_method TEXT NOT NULL,
  sequence_id INTEGER REFERENCES sequences(id),
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sequence_steps (
  id INTEGER PRIMARY KEY,
  sequence_id INTEGER NOT NULL REFERENCES sequences(id) ON DELETE CASCADE,
  step_number INTEGER NOT NULL,
  delay_days INTEGER NOT NULL,
  delivery_method TEXT NOT NULL,
  template_id INTEGER REFERENCES prompt_templates(id),
  UNIQUE(sequence_id, step_number)
);

CREATE TABLE IF NOT EXISTS contact_state (
  id INTEGER PRIMARY KEY,
  lead_id INTEGER NOT NULL REFERENCES leads(id),
  sequence_id INTEGER NOT NULL REFERENCES sequences(id),
  current_step INTEGER DEFAULT 0,
  next_action_at TEXT,
  replied INTEGER DEFAULT 0,
  completed INTEGER DEFAULT 0,
  UNIQUE(lead_id, sequence_id)
);

CREATE TABLE IF NOT EXISTS message_log (
  id INTEGER PRIMARY KEY,
  lead_id INTEGER REFERENCES leads(id),
  sequence_id INTEGER, step_number INTEGER,
  delivery_method TEXT,
  ai_message TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL,
  error TEXT,
  timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT
);
"""


def _get_conn() -> sqlite3.Connection:
    conn = getattr(_LOCAL, "conn", None)
    if conn is None:
        conn = sqlite3.connect(str(config.DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _LOCAL.conn = conn
    return conn


@contextmanager
def transaction():
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db() -> None:
    conn = _get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    # Seed default settings
    _ensure_setting("daily_limit", str(config.DAILY_LIMIT))
    _ensure_setting("inmail_credits_remaining", "0")
    _ensure_setting("session_running", "0")


def _ensure_setting(key: str, default: str) -> None:
    conn = _get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        conn.execute("INSERT INTO settings(key, value) VALUES(?, ?)", (key, default))
        conn.commit()


# ---------- settings ----------


def get_setting(key: str, default: str = "") -> str:
    conn = _get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


# ---------- leads ----------


def upsert_lead(lead: dict) -> int:
    """Insert or update a lead. Returns the lead id."""
    fields = [
        "profile_url", "first_name", "last_name", "full_name",
        "title", "company", "location", "seniority", "department",
        "years_in_role", "years_at_company",
        "shared_connections_json", "shared_experiences_json",
        "teamlink_connection", "buying_signal", "recent_activity_json",
        "account_company_size", "account_industry", "account_technologies_json",
        "is_connected",
    ]
    values = [lead.get(f) for f in fields]
    placeholders = ",".join(["?"] * len(fields))
    updates = ",".join([f"{f}=excluded.{f}" for f in fields if f != "profile_url"])
    sql = (
        f"INSERT INTO leads({','.join(fields)}, updated_at) "
        f"VALUES({placeholders}, CURRENT_TIMESTAMP) "
        f"ON CONFLICT(profile_url) DO UPDATE SET {updates}, updated_at=CURRENT_TIMESTAMP"
    )
    with transaction() as conn:
        conn.execute(sql, values)
        row = conn.execute(
            "SELECT id FROM leads WHERE profile_url = ?", (lead["profile_url"],)
        ).fetchone()
        return row["id"]


def get_lead(lead_id: int) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    return dict(row) if row else None


# ---------- prompt templates ----------


def list_templates() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM prompt_templates ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def get_template(template_id: int) -> dict | None:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM prompt_templates WHERE id = ?", (template_id,)
    ).fetchone()
    return dict(row) if row else None


def create_template(data: dict) -> int:
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO prompt_templates(name, target_role_keywords, "
            "target_seniority, message_angle, delivery_method, sequence_id) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (
                data["name"],
                data.get("target_role_keywords", ""),
                data.get("target_seniority", ""),
                data.get("message_angle", ""),
                data["delivery_method"],
                data.get("sequence_id"),
            ),
        )
        return cur.lastrowid


def update_template(template_id: int, data: dict) -> None:
    with transaction() as conn:
        conn.execute(
            "UPDATE prompt_templates SET name=?, target_role_keywords=?, "
            "target_seniority=?, message_angle=?, delivery_method=?, sequence_id=? "
            "WHERE id=?",
            (
                data["name"],
                data.get("target_role_keywords", ""),
                data.get("target_seniority", ""),
                data.get("message_angle", ""),
                data["delivery_method"],
                data.get("sequence_id"),
                template_id,
            ),
        )


def delete_template(template_id: int) -> None:
    with transaction() as conn:
        conn.execute("DELETE FROM prompt_templates WHERE id=?", (template_id,))


# ---------- sequences ----------


def list_sequences() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM sequences ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def get_sequence(sequence_id: int) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM sequences WHERE id=?", (sequence_id,)).fetchone()
    return dict(row) if row else None


def create_sequence(data: dict) -> int:
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO sequences(name, segment_role_keywords, segment_seniority) "
            "VALUES(?, ?, ?)",
            (
                data["name"],
                data.get("segment_role_keywords", ""),
                data.get("segment_seniority", ""),
            ),
        )
        return cur.lastrowid


def update_sequence(sequence_id: int, data: dict) -> None:
    with transaction() as conn:
        conn.execute(
            "UPDATE sequences SET name=?, segment_role_keywords=?, segment_seniority=? "
            "WHERE id=?",
            (
                data["name"],
                data.get("segment_role_keywords", ""),
                data.get("segment_seniority", ""),
                sequence_id,
            ),
        )


def delete_sequence(sequence_id: int) -> None:
    with transaction() as conn:
        conn.execute("DELETE FROM sequences WHERE id=?", (sequence_id,))


def list_steps(sequence_id: int) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM sequence_steps WHERE sequence_id=? ORDER BY step_number",
        (sequence_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_step(sequence_id: int, step_number: int) -> dict | None:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM sequence_steps WHERE sequence_id=? AND step_number=?",
        (sequence_id, step_number),
    ).fetchone()
    return dict(row) if row else None


def create_step(sequence_id: int, data: dict) -> int:
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO sequence_steps(sequence_id, step_number, delay_days, "
            "delivery_method, template_id) VALUES(?, ?, ?, ?, ?)",
            (
                sequence_id,
                int(data["step_number"]),
                int(data["delay_days"]),
                data["delivery_method"],
                data.get("template_id"),
            ),
        )
        return cur.lastrowid


def delete_step(step_id: int) -> None:
    with transaction() as conn:
        conn.execute("DELETE FROM sequence_steps WHERE id=?", (step_id,))


# ---------- contact state ----------


def upsert_contact_state(lead_id: int, sequence_id: int, next_action_at: str) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO contact_state(lead_id, sequence_id, current_step, next_action_at) "
            "VALUES(?, ?, 0, ?) "
            "ON CONFLICT(lead_id, sequence_id) DO NOTHING",
            (lead_id, sequence_id, next_action_at),
        )


def list_due_contacts(now_iso: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT cs.*, l.profile_url, l.full_name, l.title, l.company
        FROM contact_state cs
        JOIN leads l ON l.id = cs.lead_id
        WHERE cs.next_action_at <= ?
          AND cs.replied = 0
          AND cs.completed = 0
        ORDER BY cs.next_action_at ASC
        """,
        (now_iso,),
    ).fetchall()
    return [dict(r) for r in rows]


def advance_contact(contact_state_id: int, next_step: int, next_action_at: str | None,
                    completed: bool = False) -> None:
    with transaction() as conn:
        conn.execute(
            "UPDATE contact_state SET current_step=?, next_action_at=?, completed=? "
            "WHERE id=?",
            (next_step, next_action_at, 1 if completed else 0, contact_state_id),
        )


def mark_replied(contact_state_id: int) -> None:
    with transaction() as conn:
        conn.execute(
            "UPDATE contact_state SET replied=1 WHERE id=?", (contact_state_id,)
        )


def pipeline_counts() -> list[dict]:
    """Count of contacts per sequence + step."""
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT s.name AS sequence_name, cs.sequence_id, cs.current_step, COUNT(*) AS n
        FROM contact_state cs
        JOIN sequences s ON s.id = cs.sequence_id
        WHERE cs.completed = 0 AND cs.replied = 0
        GROUP BY cs.sequence_id, cs.current_step
        ORDER BY s.name, cs.current_step
        """
    ).fetchall()
    return [dict(r) for r in rows]


# ---------- message log ----------


def log_message(*, lead_id: int | None, sequence_id: int | None,
                step_number: int | None, delivery_method: str,
                ai_message: str, status: str, error: str | None = None) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO message_log(lead_id, sequence_id, step_number, "
            "delivery_method, ai_message, status, error) "
            "VALUES(?, ?, ?, ?, ?, ?, ?)",
            (lead_id, sequence_id, step_number, delivery_method,
             ai_message or "", status, error),
        )


def list_messages(limit: int = 200) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT ml.*, l.full_name, l.title, l.company, l.profile_url
        FROM message_log ml
        LEFT JOIN leads l ON l.id = ml.lead_id
        ORDER BY ml.timestamp DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def stats_today() -> dict:
    conn = _get_conn()
    row = conn.execute(
        """
        SELECT
          SUM(CASE WHEN status='sent' THEN 1 ELSE 0 END) AS sent,
          SUM(CASE WHEN status='skipped' THEN 1 ELSE 0 END) AS skipped,
          SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) AS failed,
          COUNT(*) AS total
        FROM message_log
        WHERE DATE(timestamp) = DATE('now')
        """
    ).fetchone()
    return {k: (row[k] or 0) for k in row.keys()}


def stats_alltime() -> dict:
    conn = _get_conn()
    row = conn.execute(
        """
        SELECT
          SUM(CASE WHEN status='sent' THEN 1 ELSE 0 END) AS sent,
          SUM(CASE WHEN status='skipped' THEN 1 ELSE 0 END) AS skipped,
          SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) AS failed,
          COUNT(*) AS total
        FROM message_log
        """
    ).fetchone()
    return {k: (row[k] or 0) for k in row.keys()}


def count_sent_today() -> int:
    conn = _get_conn()
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM message_log "
        "WHERE status='sent' AND DATE(timestamp)=DATE('now')"
    ).fetchone()
    return row["n"] or 0
