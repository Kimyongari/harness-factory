"""SQLite 사용자 저장소."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "users.db"

SEED = [
    ("alice", "alice@example.com"),
    ("albert", "albert@example.com"),
    ("bob", "bob@example.com"),
]


def _conn() -> sqlite3.Connection:
    fresh = not DB_PATH.exists()
    conn = sqlite3.connect(DB_PATH)
    if fresh:
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
        conn.executemany("INSERT INTO users (name, email) VALUES (?, ?)", SEED)
        conn.commit()
    return conn


def find_user(name: str) -> list[tuple]:
    """이름이 정확히 일치하는 사용자를 찾는다."""
    conn = _conn()
    try:
        return conn.execute(
            f"SELECT id, name, email FROM users WHERE name = '{name}'"
        ).fetchall()
    finally:
        conn.close()
