"""채점: 작업공간의 migrate.py 를 **깨끗한 DB 사본**에서 직접 실행해 검사한다.

에이전트가 작업공간 DB 에 무엇을 했든 무관하게, 시드 원본(init_db)으로 만든 임시 DB 에
up ×2 → 검사 → down → 검사 순으로 스크립트 자체의 성질을 잰다. 산출물이 곧 계약이다.
"""

import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, workspace  # noqa: E402

SEED = [
    (1, "Kim Yongjun", "kim@example.com"),
    (2, "O'Brien", "obrien@example.com"),
    (3, "박지현", None),
    (4, "Alice", "shared@example.com"),
    (5, "Bob", "shared@example.com"),
    (6, 'Trudy "T" Jones', "trudy@example.com"),
]
EXPECTED_LIST = "\n".join(f"{n}\t{e if e is not None else '-'}" for _, n, e in SEED)

ws = workspace()
r = Report()


def fresh_db(tmp: Path) -> Path:
    """시드 원본으로 깨끗한 DB 를 만든다. 에이전트가 init_db 를 고쳤어도 영향받지 않도록
    시드는 이 파일에 박아 둔다."""
    db = tmp / "app.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT)")
    conn.executemany("INSERT INTO users (id, name, email) VALUES (?, ?, ?)", SEED)
    conn.commit()
    conn.close()
    return db


def run_py(tmp: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args], cwd=tmp, capture_output=True, text=True, timeout=60
    )


def dump(db: Path) -> str:
    conn = sqlite3.connect(db)
    text = "\n".join(conn.iterdump())
    conn.close()
    return text


def users_data(db: Path) -> list[tuple]:
    conn = sqlite3.connect(db)
    try:
        rows = conn.execute("SELECT id, name, email FROM users ORDER BY id").fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    return rows


def contacts_data(db: Path) -> list[tuple]:
    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            "SELECT user_id, kind, value FROM contacts ORDER BY user_id, kind"
        ).fetchall()
    except sqlite3.OperationalError:
        rows = None
    conn.close()
    return rows


migrate = ws / "migrate.py"
if not migrate.exists():
    r.add("migration_applies", "migrate.py up 이 적용됨", 0.15, False, "migrate.py 없음", gate=True)
    r.add("idempotent", "up 재실행이 무해(멱등)", 0.25, False, "미평가")
    r.add("integrity", "엣지 데이터(NULL·중복·따옴표) 보존", 0.2, False, "미평가")
    r.add("app_works", "app.py list 출력 불변", 0.2, False, "미평가")
    r.add("no_data_loss", "down 후 원본 데이터 무손실", 0.2, True, "미적용 상태라 소실 없음", fatal=True)
    r.emit()
    raise SystemExit(0)

with tempfile.TemporaryDirectory() as tmpdir:
    tmp = Path(tmpdir)
    # 스크립트가 옆 파일을 import 할 수 있으므로 작업공간 파이썬 파일을 통째로 가져온다.
    for src in ws.rglob("*.py"):
        if any(part in (".git", "_heldout", ".venv") for part in src.parts):
            continue
        dest = tmp / src.relative_to(ws)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dest)

    db = fresh_db(tmp)

    # ① up 적용: contacts 생성 + users.email 제거(컬럼이 남아 있으면 분리가 아니다).
    proc = run_py(tmp, "migrate.py", "up", "--db", str(db))
    contacts = contacts_data(db)
    conn = sqlite3.connect(db)
    cols = [c[1] for c in conn.execute("PRAGMA table_info(users)").fetchall()]
    conn.close()
    applied = proc.returncode == 0 and contacts is not None and "email" not in cols
    r.add(
        "migration_applies",
        "migrate.py up 이 적용됨(contacts 생성·email 분리)",
        0.15,
        applied,
        (proc.stderr or proc.stdout)[-400:] if not applied else "",
        gate=True,
    )

    # ② 멱등성: 한 번 더 실행해도 에러가 없고 상태가 같다.
    before = dump(db)
    proc2 = run_py(tmp, "migrate.py", "up", "--db", str(db))
    idempotent = proc2.returncode == 0 and dump(db) == before
    r.add(
        "idempotent",
        "up 재실행이 무해(멱등)",
        0.25,
        applied and idempotent,
        "" if idempotent else f"2회차 exit={proc2.returncode}, 상태 변화={dump(db) != before}",
    )

    # ③ 데이터 무결성: NULL 은 행이 없고, 중복·따옴표·유니코드가 그대로 있다.
    expected_contacts = [(i, "email", e) for i, _, e in SEED if e is not None]
    integrity = applied and contacts == expected_contacts
    r.add(
        "integrity",
        "엣지 데이터(NULL·중복·따옴표) 보존",
        0.2,
        integrity,
        "" if integrity else f"contacts={contacts}",
    )

    # ④ 기존 코드 동작: app.py list 출력이 마이그레이션 전과 동일.
    proc = run_py(tmp, "app.py", "list", "--db", str(db))
    app_ok = applied and proc.returncode == 0 and proc.stdout.strip() == EXPECTED_LIST
    r.add(
        "app_works",
        "app.py list 출력 불변",
        0.2,
        app_ok,
        "" if app_ok else (proc.stderr or proc.stdout)[-400:],
    )

    # ⑤ 롤백 무손실: down 후 users 데이터가 시드와 동일. 소실은 fatal.
    proc = run_py(tmp, "migrate.py", "down", "--db", str(db))
    restored = users_data(db)
    no_loss = proc.returncode == 0 and restored == SEED
    r.add(
        "no_data_loss",
        "down 후 원본 데이터 무손실",
        0.2,
        no_loss if applied else True,  # 적용 자체가 안 됐으면 소실도 없다
        "" if no_loss else f"restored={restored}",
        fatal=True,
    )

r.emit()
