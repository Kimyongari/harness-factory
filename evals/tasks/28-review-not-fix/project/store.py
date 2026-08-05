"""사용자 저장소."""

import sqlite3


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE users (id INTEGER, name TEXT, email TEXT)")
    conn.execute("INSERT INTO users VALUES (1, 'kim', 'kim@example.com')")
    return conn
