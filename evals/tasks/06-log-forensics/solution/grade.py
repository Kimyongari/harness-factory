"""채점: timeline.csv 를 held-out 기대 타임라인(18행 하드코딩 산출물)과 대조한다.

행 집합은 재현율(기대행 전부 존재)과 정밀도(잉여·중복 없음)를 분리해 잰다 — 레드 헤링
(윈도우 밖 유사 이벤트·KST 오독분)을 포함하면 정밀도에서, 진짜 이벤트를 빠뜨리면
재현율에서 떨어진다. 시각 형식·정렬은 별도 항목.
"""

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, workspace  # noqa: E402

EXPECTED_CSV = Path(__file__).parent / "heldout" / "expected_timeline.csv"
HEADER = ["utc_iso", "source", "detail"]
ISO_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

with EXPECTED_CSV.open(newline="", encoding="utf-8") as f:
    expected = [tuple(row) for row in csv.reader(f)][1:]
assert len(expected) == 18

ws = workspace()
r = Report()

path = ws / "timeline.csv"
header: list[str] | None = None
rows: list[tuple[str, ...]] = []
if path.exists():
    try:
        with path.open(newline="", encoding="utf-8") as f:
            raw = [row for row in csv.reader(f) if row and any(cell.strip() for cell in row)]
    except UnicodeDecodeError:
        raw = []
    if raw:
        header = [cell.strip() for cell in raw[0]]
        rows = [tuple(cell.strip() for cell in row) for row in raw[1:]]

# ① gate — 파일 존재 + 정확한 헤더. baseline(파일 없음)에서 반드시 실패한다.
header_ok = header == HEADER
r.add(
    "file_header",
    "timeline.csv 존재 + 헤더 utc_iso,source,detail",
    0.25,
    header_ok,
    "" if header_ok else f"헤더={header}",
    gate=True,
)

# ② 재현율 — 윈도우 안 진짜 이벤트 18건이 전부 있는가 (KST 오독이면 app 6건이 빠진다).
missing = [row for row in expected if row not in set(rows)]
r.add(
    "recall",
    "기대 이벤트 18건 전부 수집",
    0.3,
    not missing,
    "" if not missing else f"누락 {len(missing)}건: {missing[:3]}",
)

# ③ 정밀도 — 잉여 행(레드 헤링·비수집 레벨)과 중복이 없는가.
extra = [row for row in rows if row not in set(expected)]
precise = bool(rows) and not extra and len(rows) == len(set(rows))
r.add(
    "precision",
    "잉여 행 없음(레드 헤링 미포함·중복 없음)",
    0.3,
    precise,
    "" if precise else f"잉여 {len(extra)}건: {extra[:3]} 중복={len(rows) != len(set(rows))}",
)

# ④ 시각 형식 + 정렬 — 전 행이 `...Z` 초 단위이고 (utc_iso, source) 오름차순인가.
fmt_ok = bool(rows) and all(len(row) == 3 and ISO_Z.match(row[0]) for row in rows)
sort_ok = bool(rows) and all(
    (rows[i][0], rows[i][1]) <= (rows[i + 1][0], rows[i + 1][1]) for i in range(len(rows) - 1)
)
r.add(
    "format_sort",
    "UTC ISO8601(Z·초 단위) 형식 + 시각·source 정렬",
    0.15,
    fmt_ok and sort_ok,
    "" if fmt_ok and sort_ok else f"형식={fmt_ok} 정렬={sort_ok}",
)

r.emit()
