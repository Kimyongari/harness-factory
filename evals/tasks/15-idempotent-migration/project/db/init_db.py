"""시드 데이터의 단일 원본. 이 파일은 수정하지 않는다.

사용: python db/init_db.py [DB경로]  (기본 app.db)
"""

import sqlite3
import sys
from pathlib import Path

SEED = [
    (1, "Kim Yongjun", "kim@example.com"),
    (2, "O'Brien", "obrien@example.com"),
    (3, "박지현", None),
    (4, "Alice", "shared@example.com"),
    (5, "Bob", "shared@example.com"),
    (6, 'Trudy "T" Jones', "trudy@example.com"),
]


def build(db_path: str) -> None:
    path = Path(db_path)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT)"
    )
    conn.executemany("INSERT INTO users (id, name, email) VALUES (?, ?, ?)", SEED)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "app.db")
