import hashlib
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    owner_token_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    mode TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS preferences (
    owner_token_hash TEXT PRIMARY KEY,
    warmth INTEGER NOT NULL,
    humour INTEGER NOT NULL,
    sarcasm INTEGER NOT NULL,
    directness INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    owner_token_hash TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT,
    approved_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS memory_candidates (
    id TEXT PRIMARY KEY,
    owner_token_hash TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
"""


def database_path() -> Path:
    # Read fresh each call (not cached at import) so tests can monkeypatch DATABASE_PATH per test.
    return Path(os.getenv("DATABASE_PATH") or ROOT / "backend" / "data" / "bud.db")


@contextmanager
def connection():
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connection() as conn:
        conn.executescript(SCHEMA)


def hash_owner_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class SessionOwnerMismatch(Exception):
    """Raised when a client reuses a session_id that belongs to a different visitor."""


def ensure_session(session_id: str, owner_token_hash: str, created_at: str) -> None:
    with connection() as conn:
        row = conn.execute("SELECT owner_token_hash FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO sessions (id, owner_token_hash, created_at) VALUES (?, ?, ?)",
                (session_id, owner_token_hash, created_at),
            )
        elif row["owner_token_hash"] != owner_token_hash:
            raise SessionOwnerMismatch(session_id)


def save_turns(session_id: str, turns: list[dict]) -> None:
    with connection() as conn:
        conn.executemany(
            "INSERT INTO messages (id, session_id, role, content, mode, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            [(t["id"], session_id, t["role"], t["content"], t.get("mode"), t["created_at"]) for t in turns],
        )


def get_preferences(owner_token_hash: str) -> dict | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT warmth, humour, sarcasm, directness FROM preferences WHERE owner_token_hash = ?",
            (owner_token_hash,),
        ).fetchone()
        return dict(row) if row else None


def save_preferences(owner_token_hash: str, prefs: dict, updated_at: str) -> None:
    with connection() as conn:
        conn.execute(
            """INSERT INTO preferences (owner_token_hash, warmth, humour, sarcasm, directness, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(owner_token_hash) DO UPDATE SET
                 warmth = excluded.warmth, humour = excluded.humour, sarcasm = excluded.sarcasm,
                 directness = excluded.directness, updated_at = excluded.updated_at""",
            (owner_token_hash, prefs["warmth"], prefs["humour"], prefs["sarcasm"], prefs["directness"], updated_at),
        )


def create_memory_candidate(candidate_id: str, owner_token_hash: str, content: str, category: str | None, created_at: str, expires_at: str) -> None:
    with connection() as conn:
        conn.execute(
            "INSERT INTO memory_candidates (id, owner_token_hash, content, category, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
            (candidate_id, owner_token_hash, content, category, created_at, expires_at),
        )


def get_memory_candidate(candidate_id: str, owner_token_hash: str, now: str) -> dict | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT id, content, category FROM memory_candidates WHERE id = ? AND owner_token_hash = ? AND expires_at > ?",
            (candidate_id, owner_token_hash, now),
        ).fetchone()
        return dict(row) if row else None


def get_latest_pending_candidate(owner_token_hash: str, now: str) -> dict | None:
    """The most recent unresolved (not approved/rejected/expired) candidate for this owner, if
    any -- used to surface a candidate extracted in the background on a later turn."""
    with connection() as conn:
        row = conn.execute(
            "SELECT id, content, category FROM memory_candidates WHERE owner_token_hash = ? AND expires_at > ? "
            "ORDER BY created_at DESC LIMIT 1",
            (owner_token_hash, now),
        ).fetchone()
        return dict(row) if row else None


def approve_memory_candidate(candidate_id: str, owner_token_hash: str, approved_at: str) -> str | None:
    """Moves an unexpired candidate into approved memories. Returns the new memory id, or None if not found/not owned/expired."""
    with connection() as conn:
        row = conn.execute(
            "SELECT content, category FROM memory_candidates WHERE id = ? AND owner_token_hash = ? AND expires_at > ?",
            (candidate_id, owner_token_hash, approved_at),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            "INSERT INTO memories (id, owner_token_hash, content, category, approved_at, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (candidate_id, owner_token_hash, row["content"], row["category"], approved_at, approved_at),
        )
        conn.execute("DELETE FROM memory_candidates WHERE id = ? AND owner_token_hash = ?", (candidate_id, owner_token_hash))
        return candidate_id


def reject_memory_candidate(candidate_id: str, owner_token_hash: str) -> bool:
    with connection() as conn:
        cursor = conn.execute(
            "DELETE FROM memory_candidates WHERE id = ? AND owner_token_hash = ?", (candidate_id, owner_token_hash)
        )
        return cursor.rowcount > 0


def list_memories(owner_token_hash: str) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, content, category, approved_at FROM memories WHERE owner_token_hash = ? ORDER BY approved_at DESC",
            (owner_token_hash,),
        ).fetchall()
        return [dict(row) for row in rows]


def delete_memory(memory_id: str, owner_token_hash: str) -> bool:
    with connection() as conn:
        cursor = conn.execute("DELETE FROM memories WHERE id = ? AND owner_token_hash = ?", (memory_id, owner_token_hash))
        return cursor.rowcount > 0
