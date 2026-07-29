"""마이그레이션 적용기."""

from __future__ import annotations

import sqlite3
from pathlib import Path

MIGRATIONS = Path(__file__).parent / "migrations"


def apply_migrations(conn: sqlite3.Connection) -> None:
    """migrations/ 의 .sql 파일을 이름 순서대로 적용한다."""
    for path in sorted(MIGRATIONS.glob("*.sql")):
        conn.executescript(path.read_text(encoding="utf-8"))
    conn.commit()


def columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
