import sqlite3
import time
from pathlib import Path

DB_PATH = Path("outputs/subtitle_cache.db")


def _get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subtitle_cache (
            video_id      TEXT PRIMARY KEY,
            status        TEXT,
            language      TEXT,
            checked_at    REAL,
            expires_at    REAL
        )
    """)
    conn.commit()
    return conn


def get_status(video_id: str) -> str | None:
    conn = _get_db()
    cur = conn.execute(
        "SELECT status FROM subtitle_cache WHERE video_id = ? AND expires_at > ?",
        (video_id, time.time()),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def set_status(video_id: str, status: str, language: str = "en"):
    conn = _get_db()
    now = time.time()

    if status == "AVAILABLE":
        ttl = 7 * 24 * 3600
    elif status == "MISSING":
        ttl = 24 * 3600
    elif status == "RATE_LIMITED":
        ttl = 15 * 60
    else:
        ttl = 0

    expires_at = now + ttl

    conn.execute(
        """
        INSERT INTO subtitle_cache (video_id, status, language, checked_at, expires_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(video_id) DO UPDATE SET
            status=excluded.status,
            language=excluded.language,
            checked_at=excluded.checked_at,
            expires_at=excluded.expires_at
        """,
        (video_id, status, language, now, expires_at),
    )
    conn.commit()
    conn.close()
