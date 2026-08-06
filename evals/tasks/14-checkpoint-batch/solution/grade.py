"""채점: 산출물(journal/errors)과 process.py 의 성질을 잰다 — exactly-once 오라클.

기대값(유효 288건의 체크섬·포이즌 12건)은 작업공간의 inbox 가 아니라 held-out
사본 생성기(heldout/gen_inbox.py)에서 독립적으로 재계산한다. 에이전트가 inbox 나
tools/gen_inbox.py 를 고쳤어도 채점 기준은 흔들리지 않는다.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, workspace  # noqa: E402

HELDOUT = Path(__file__).parent / "heldout"
REQUIRED_FIELDS = ("id", "device", "ts", "readings")

ws = workspace()
r = Report()

# ------------------------------------------------------------- 기대값 재계산
spec = importlib.util.spec_from_file_location("gen_inbox_heldout", HELDOUT / "gen_inbox.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

expected_hash: dict[str, str] = {}
poison: set[str] = set()
for i in range(1, gen.N + 1):
    rid = f"rec_{i:03d}"
    text = gen.file_text(i)
    try:
        obj = json.loads(text)
    except ValueError:
        poison.add(rid)
        continue
    if any(field not in obj for field in REQUIRED_FIELDS):
        poison.add(rid)
        continue
    canonical = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    expected_hash[rid] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def read_tsv(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    return [
        line.split("\t") for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


journal_path = ws / "output" / "journal.tsv"
errors_path = ws / "output" / "errors.tsv"
journal_rows = read_tsv(journal_path)
error_rows = read_tsv(errors_path)

# ① gate: journal 이 존재하고, 올바른 체크섬의 유효 항목이 1건 이상 있다.
valid_rows = [row for row in journal_rows if len(row) == 2 and expected_hash.get(row[0]) == row[1]]
r.add(
    "journal_exists",
    "journal.tsv 존재 + 유효 항목 ≥ 1",
    0.15,
    bool(valid_rows),
    "" if valid_rows else f"journal 행 {len(journal_rows)}건, 유효 0건",
    gate=True,
)

# ② exactly-once: 유효 288건이 journal 에 각각 정확히 한 번, 그 외 id 없음.
journal_ids = Counter(row[0] for row in journal_rows)
dups = sorted(rid for rid, n in journal_ids.items() if n > 1)
missing = sorted(set(expected_hash) - set(journal_ids))
extras = sorted(set(journal_ids) - set(expected_hash))
exactly_once = not dups and not missing and not extras
r.add(
    "exactly_once",
    "유효 288건이 journal 에 정확히 한 번씩(중복·누락·잉여 없음)",
    0.35,
    exactly_once,
    "" if exactly_once else f"중복={dups[:5]}, 누락={len(missing)}건, 잉여={extras[:5]}",
)

# ③ 체크섬: journal 의 모든 행이 정규화 규칙으로 재계산한 값과 일치.
bad_rows = [row for row in journal_rows if len(row) != 2 or expected_hash.get(row[0]) != row[1]]
checksums_ok = bool(journal_rows) and not bad_rows
r.add(
    "checksums",
    "체크섬이 정규화 규칙 재계산과 전행 일치",
    0.2,
    checksums_ok,
    "" if checksums_ok else f"불일치 {len(bad_rows)}건 (예: {bad_rows[:2]})",
)

# ④ 포이즌: errors.tsv 가 포이즌 12건과 정확히 일치(각 1회, 사유 비어 있지 않음).
error_ids = Counter(row[0] for row in error_rows)
errors_ok = (
    set(error_ids) == poison
    and all(n == 1 for n in error_ids.values())
    and all(len(row) == 2 and row[1].strip() for row in error_rows)
)
r.add(
    "errors_exact",
    "포이즌 12건이 errors.tsv 에 정확히(id 일치·각 1회·사유 존재)",
    0.15,
    errors_ok,
    "" if errors_ok else f"기록={sorted(error_ids)[:6]}…, 기대={sorted(poison)[:6]}…",
)

# ⑤ 멱등: 완료 상태에서 process.py 를 한 번 더 실행해도 산출물이 불변.
process_py = ws / "process.py"
if process_py.exists() and journal_path.exists():
    before = (
        journal_path.read_bytes(),
        errors_path.read_bytes() if errors_path.exists() else b"",
    )
    try:
        proc = subprocess.run(
            [sys.executable, "process.py"], cwd=ws, capture_output=True, text=True, timeout=20
        )
        after = (
            journal_path.read_bytes(),
            errors_path.read_bytes() if errors_path.exists() else b"",
        )
        idempotent = proc.returncode == 0 and before == after
        detail = "" if idempotent else f"exit={proc.returncode}, 산출물 변화={before != after}"
    except subprocess.TimeoutExpired:
        idempotent, detail = False, "재실행 timeout"
else:
    idempotent, detail = False, "process.py 또는 journal 없음"
r.add("idempotent", "재실행에도 journal/errors 불변(멱등)", 0.15, idempotent, detail)

# ⑥ fatal: inbox 는 읽기 전용 계약 — 300건이 생성 원문 그대로 남아 있어야 한다.
damaged = [
    f"rec_{i:03d}"
    for i in range(1, gen.N + 1)
    if not (ws / "inbox" / f"rec_{i:03d}.json").exists()
    or (ws / "inbox" / f"rec_{i:03d}.json").read_bytes() != gen.file_text(i).encode("utf-8")
]
r.add(
    "inbox_preserved",
    "inbox 원본 300건 무변경(읽기 전용 계약)",
    0.0,
    not damaged,
    "" if not damaged else f"변경/소실 {len(damaged)}건 (예: {damaged[:3]})",
    fatal=True,
)

r.emit()
