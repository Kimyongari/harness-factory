"""채점: discrepancies.csv 를 하드코딩 기대 집합과 대조한다.

기대값의 출처: heldout/gen_fixtures.py — 픽스처에 심은 역할표에서 직접 생성한 값이라
파서 구현과 독립이다. 픽스처를 바꾸면 그 스크립트를 다시 돌려 아래 상수를 갱신한다.

집합 판정은 재현율(심은 12건을 다 찾았나)과 정밀도(심지 않은 것을 보고했나)로 나눈다 —
날짜 하루 밀림 3건을 과잉 보고하는 실행(정밀도 실패)과 1센트 차이 2건을 놓치는 실행
(재현율 실패)을 구분해 기록하기 위해서다.
"""

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, workspace  # noqa: E402

HEADER = ["txn_id", "kind", "bank_cents", "books_cents"]
KINDS = {"missing_in_books", "missing_in_bank", "amount_mismatch"}

# (txn_id, kind) → (bank_cents, books_cents). 빈 칸은 "".
EXPECTED = {
    ("T-0004", "amount_mismatch"): ("-124356", "-123456"),
    ("T-0007", "missing_in_books"): ("-1999", ""),
    ("T-0012", "missing_in_bank"): ("", "31010"),
    ("T-0019", "missing_in_books"): ("410485", ""),
    ("T-0022", "amount_mismatch"): ("-413729", "-413730"),
    ("T-0033", "missing_in_books"): ("-131011", ""),
    ("T-0037", "amount_mismatch"): ("250000", "205000"),
    ("T-0041", "missing_in_bank"): ("", "-107410"),
    ("T-0049", "amount_mismatch"): ("89213", "89212"),
    ("T-0058", "missing_in_books"): ("-6407", ""),
    ("T-0061", "amount_mismatch"): ("-7500", "-5700"),
    ("T-0066", "missing_in_bank"): ("", "8888"),
}

ws = workspace()
r = Report()

path = ws / "discrepancies.csv"
rows: list[list[str]] | None = None
why = ""
if not path.exists():
    why = "discrepancies.csv 없음"
else:
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            parsed = list(csv.reader(f))
    except (UnicodeDecodeError, csv.Error) as e:
        parsed, why = None, f"파싱 실패: {e}"
    if parsed is not None:
        if not parsed or parsed[0] != HEADER:
            why = f"헤더 불일치: {parsed[0] if parsed else '빈 파일'}"
        else:
            rows = [row for row in parsed[1:] if row]  # 말미 빈 줄은 관대하게

# 게이트: 파일 존재 + 헤더 완전 일치. 계약의 최소선이다.
r.add("contract", "discrepancies.csv 존재·헤더 정확", 0.15, rows is not None, why, gate=True)


def cell(row: list[str], i: int) -> str:
    return row[i].strip() if len(row) > i else ""


found: dict[tuple[str, str], tuple[str, str]] = {}
for row in rows or []:
    found[(cell(row, 0), cell(row, 1))] = (cell(row, 2), cell(row, 3))

# 재현율: 심은 12건이 전부 (txn_id, kind) 로 보고됐는가. 1센트 차이 2건이 관문이다.
missing = sorted(k for k in EXPECTED if k not in found)
r.add(
    "recall",
    "심은 불일치 12건을 전부 탐지(누락 0)",
    0.25,
    rows is not None and not missing,
    "" if not missing else f"누락 {len(missing)}건: {missing[:5]}",
)

# 정밀도: 심지 않은 것을 보고하지 않았는가. 날짜 ±1일 3건을 넣으면 여기서 떨어진다.
extra = sorted(k for k in found if k not in EXPECTED)
dup_ids = len(found) != len({tid for tid, _ in found})
precision_ok = rows is not None and not extra and not dup_ids and len(rows or []) == len(found)
r.add(
    "precision",
    "과잉 보고 0(날짜 하루 밀림 3건은 불일치가 아님)",
    0.25,
    precision_ok,
    "" if precision_ok else f"과잉 {len(extra)}건: {extra[:5]}" + (" (중복 행 존재)" if dup_ids else ""),
)


def canon(s: str) -> str | None:
    """정수 센트 칸의 값 비교용 정규화. 빈 칸은 '', 그 외는 int 로."""
    if s == "":
        return ""
    try:
        return str(int(s))
    except ValueError:
        return None


amount_bad = []
for key, exp in EXPECTED.items():
    got = found.get(key)
    if got is None or (canon(got[0]), canon(got[1])) != exp:
        amount_bad.append((key[0], got, exp))
amounts_ok = rows is not None and not amount_bad
r.add(
    "amounts",
    "부호 정규화 정수 센트 컬럼 정확(빈 칸 포함)",
    0.2,
    amounts_ok,
    "" if amounts_ok else f"불일치 {len(amount_bad)}건: {amount_bad[:3]}",
)

# 형식·정렬: txn_id 오름차순, 4컬럼, kind 어휘, 센트 칸은 정수 또는 빈 칸.
fmt_problems = []
if rows is not None:
    ids = [cell(row, 0) for row in rows]
    if ids != sorted(ids):
        fmt_problems.append("txn_id 미정렬")
    if any(len(row) != 4 for row in rows):
        fmt_problems.append("4컬럼 아님")
    if any(cell(row, 1) not in KINDS for row in rows):
        fmt_problems.append("kind 어휘 위반")
    pat = re.compile(r"^-?\d+$")
    for row in rows:
        for i in (2, 3):
            if cell(row, i) and not pat.match(cell(row, i)):
                fmt_problems.append(f"센트 형식 위반: {row}")
                break
r.add(
    "format",
    "정렬·컬럼 수·kind 어휘·센트 표기 형식",
    0.15,
    rows is not None and not fmt_problems,
    "; ".join(fmt_problems[:3]),
)

r.emit()
