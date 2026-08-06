"""email → contacts 마이그레이션. 멱등성은 PRAGMA user_version 으로 보장한다."""

import argparse
import sqlite3


def up(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        if conn.execute("PRAGMA user_version").fetchone()[0] >= 1:
            return  # 이미 적용됨 — 멱등
        conn.execute("BEGIN")
        conn.execute(
            "CREATE TABLE contacts ("
            " id INTEGER PRIMARY KEY,"
            " user_id INTEGER NOT NULL REFERENCES users(id),"
            " kind TEXT NOT NULL,"
            " value TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO contacts (user_id, kind, value)"
            " SELECT id, 'email', email FROM users WHERE email IS NOT NULL ORDER BY id"
        )
        conn.execute("CREATE TABLE users_new (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
        conn.execute("INSERT INTO users_new (id, name) SELECT id, name FROM users")
        conn.execute("DROP TABLE users")
        conn.execute("ALTER TABLE users_new RENAME TO users")
        conn.execute("PRAGMA user_version = 1")
        conn.commit()
    finally:
        conn.close()


def down(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        if conn.execute("PRAGMA user_version").fetchone()[0] < 1:
            return  # 적용 전 — 멱등
        conn.execute("BEGIN")
        conn.execute(
            "CREATE TABLE users_old (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT)"
        )
        conn.execute(
            "INSERT INTO users_old (id, name, email)"
            " SELECT u.id, u.name,"
            "  (SELECT value FROM contacts c WHERE c.user_id = u.id AND c.kind = 'email')"
            " FROM users u"
        )
        conn.execute("DROP TABLE users")
        conn.execute("ALTER TABLE users_old RENAME TO users")
        conn.execute("DROP TABLE contacts")
        conn.execute("PRAGMA user_version = 0")
        conn.commit()
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["up", "down"])
    parser.add_argument("--db", default="app.db")
    args = parser.parse_args()
    (up if args.command == "up" else down)(args.db)


if __name__ == "__main__":
    main()
