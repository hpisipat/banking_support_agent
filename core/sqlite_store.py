import json
import os
import sqlite3
from datetime import datetime
from threading import Lock

DB_PATH = os.path.join("data", "banking_agent.db")

_INIT_LOCK = Lock()
_INITIALIZED = False


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_user_id(user_id, persona):
    value = (user_id or "").strip()
    if value:
        return value
    return f"persona::{persona}"


def init_db():
    global _INITIALIZED
    if _INITIALIZED:
        return

    with _INIT_LOCK:
        if _INITIALIZED:
            return

        os.makedirs("data", exist_ok=True)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_memory (
                    user_id TEXT NOT NULL,
                    persona TEXT NOT NULL,
                    data TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, persona)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    user_id TEXT NOT NULL,
                    persona TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    positive INTEGER NOT NULL DEFAULT 0,
                    negative INTEGER NOT NULL DEFAULT 0,
                    comments TEXT NOT NULL DEFAULT '[]',
                    last_rated TEXT,
                    PRIMARY KEY (user_id, persona, intent)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    persona TEXT NOT NULL,
                    chat_history TEXT NOT NULL DEFAULT '[]',
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    last_intent TEXT NOT NULL DEFAULT 'unknown',
                    session_data TEXT NOT NULL DEFAULT '{}',
                    memory_json TEXT NOT NULL DEFAULT '{}',
                    memory_context TEXT NOT NULL DEFAULT '',
                    is_returning INTEGER NOT NULL DEFAULT 0,
                    ended INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user
                ON sessions (user_id, persona, updated_at)
            """)
            conn.commit()

        _INITIALIZED = True


def _connect():
    init_db()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def load_memory_record(user_id, persona):
    resolved_user_id = normalize_user_id(user_id, persona)
    with _connect() as conn:
        row = conn.execute(
            "SELECT data FROM user_memory WHERE user_id = ? AND persona = ?",
            (resolved_user_id, persona)
        ).fetchone()
    if not row:
        return {}
    try:
        return json.loads(row["data"])
    except Exception:
        return {}


def save_memory_record(user_id, persona, memory):
    resolved_user_id = normalize_user_id(user_id, persona)
    payload = json.dumps(memory)
    now = _now()
    with _connect() as conn:
        conn.execute("""
            INSERT INTO user_memory (user_id, persona, data, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, persona) DO UPDATE SET
                data = excluded.data,
                updated_at = excluded.updated_at
        """, (resolved_user_id, persona, payload, now))
        conn.commit()


def clear_memory_records(user_id=None, persona=None):
    with _connect() as conn:
        if user_id and persona:
            conn.execute(
                "DELETE FROM user_memory WHERE user_id = ? AND persona = ?",
                (normalize_user_id(user_id, persona), persona)
            )
        elif persona:
            conn.execute("DELETE FROM user_memory WHERE persona = ?", (persona,))
        else:
            conn.execute("DELETE FROM user_memory")
        conn.commit()


def load_feedback_record(user_id, persona, intent):
    resolved_user_id = normalize_user_id(user_id, persona)
    with _connect() as conn:
        row = conn.execute("""
            SELECT positive, negative, comments, last_rated
            FROM feedback
            WHERE user_id = ? AND persona = ? AND intent = ?
        """, (resolved_user_id, persona, intent)).fetchone()
    if not row:
        return {
            "positive": 0,
            "negative": 0,
            "comments": [],
            "last_rated": None
        }
    try:
        comments = json.loads(row["comments"] or "[]")
    except Exception:
        comments = []
    return {
        "positive": row["positive"],
        "negative": row["negative"],
        "comments": comments,
        "last_rated": row["last_rated"]
    }


def save_feedback_record(user_id, persona, intent, record):
    resolved_user_id = normalize_user_id(user_id, persona)
    with _connect() as conn:
        conn.execute("""
            INSERT INTO feedback (
                user_id, persona, intent, positive, negative, comments, last_rated
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, persona, intent) DO UPDATE SET
                positive = excluded.positive,
                negative = excluded.negative,
                comments = excluded.comments,
                last_rated = excluded.last_rated
        """, (
            resolved_user_id,
            persona,
            intent,
            int(record.get("positive", 0)),
            int(record.get("negative", 0)),
            json.dumps(record.get("comments", [])),
            record.get("last_rated")
        ))
        conn.commit()


def load_feedback_map(user_id, persona):
    resolved_user_id = normalize_user_id(user_id, persona)
    with _connect() as conn:
        rows = conn.execute("""
            SELECT intent, positive, negative, comments, last_rated
            FROM feedback
            WHERE user_id = ? AND persona = ?
        """, (resolved_user_id, persona)).fetchall()

    result = {}
    for row in rows:
        try:
            comments = json.loads(row["comments"] or "[]")
        except Exception:
            comments = []
        result[row["intent"]] = {
            "positive": row["positive"],
            "negative": row["negative"],
            "comments": comments,
            "last_rated": row["last_rated"]
        }
    return result


def save_session_record(record):
    now = _now()
    created_at = record.get("created_at") or now
    with _connect() as conn:
        conn.execute("""
            INSERT INTO sessions (
                session_id, user_id, persona, chat_history, retry_count, last_intent,
                session_data, memory_json, memory_context, is_returning, ended,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                user_id = excluded.user_id,
                persona = excluded.persona,
                chat_history = excluded.chat_history,
                retry_count = excluded.retry_count,
                last_intent = excluded.last_intent,
                session_data = excluded.session_data,
                memory_json = excluded.memory_json,
                memory_context = excluded.memory_context,
                is_returning = excluded.is_returning,
                ended = excluded.ended,
                updated_at = excluded.updated_at
        """, (
            record["session_id"],
            record["user_id"],
            record["persona"],
            record["chat_history"],
            record["retry_count"],
            record["last_intent"],
            record["session_data"],
            record["memory_json"],
            record["memory_context"],
            int(bool(record["is_returning"])),
            int(bool(record["ended"])),
            created_at,
            now
        ))
        conn.commit()


def load_session_record(session_id):
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,)
        ).fetchone()
    return dict(row) if row else None


def delete_session_record(session_id):
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
