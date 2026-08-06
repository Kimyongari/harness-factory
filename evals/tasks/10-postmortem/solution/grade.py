"""채점: 표의 수치 6개를 heldout/fixture.py 에서 **독립 계산**한 기대값과 대조한다.

작업공간의 metrics.csv 는 신뢰하지 않는다(에이전트가 고칠 수 있다). 기대값 계산은
장애 정의(≥50 이 5분 이상 연속)를 그대로 구현하므로, 레드 헤링 스파이크(연속 4분)를
장애로 오인한 보고서는 시작·종료·지속·합·피크가 전부 어긋난다.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).parent / "heldout"))
from fixture import CAUSE_DEPLOY, incident_window  # noqa: E402
from grading import Report, workspace  # noqa: E402

SECTIONS = ["요약", "타임라인", "원인", "영향", "재발 방지"]

ws = workspace()
r = Report()

text = ""
path = ws / "postmortem.md"
if path.exists():
    text = path.read_text(encoding="utf-8", errors="ignore")


def section(name: str) -> str:
    m = re.search(rf"(?m)^##\s*{re.escape(name)}\s*$\n(.*?)(?=^##\s|\Z)", text, re.S)
    return m.group(1) if m else ""


def cell(label: str) -> str:
    """`| <라벨> | <값> |` 표 행에서 값 칸을 뽑는다. 영향 절 안에서만 찾는다."""
    m = re.search(rf"\|\s*{re.escape(label)}\s*\|\s*([^|\n]+?)\s*\|", section("영향"))
    return m.group(1).strip() if m else ""


def cell_int(label: str) -> int | None:
    m = re.search(r"\d[\d,]*", cell(label))
    return int(m.group(0).replace(",", "")) if m else None


# ① gate: 필수 절 5개 존재.
missing = [s for s in SECTIONS if not re.search(rf"(?m)^##\s*{re.escape(s)}\s*$", text)]
r.add(
    "sections",
    "필수 절 5개(요약·타임라인·원인·영향·재발 방지) 존재",
    0.15,
    bool(text) and not missing,
    f"누락: {missing}" if missing else ("postmortem.md 없음" if not text else ""),
    gate=True,
)

# ② 표의 수치 6개 — 기대값은 fixture 에서 독립 계산 (KST 로그와 무관하게 UTC 기준).
win = incident_window()
values = [
    ("start", "장애 시작(UTC)", cell("장애 시작(UTC)"), win["start"]),
    ("end", "장애 종료(UTC)", cell("장애 종료(UTC)"), win["end"]),
    ("duration", "지속 시간(분)", cell_int("지속 시간(분)"), win["duration_min"]),
    ("failed_requests", "실패 요청 수", cell_int("실패 요청 수"), win["failed_requests"]),
    ("peak_errors", "피크 분당 에러", cell_int("피크 분당 에러"), win["peak_errors"]),
    ("cause_id_cell", "원인 배포 ID(표)", cell("원인 배포 ID"), CAUSE_DEPLOY),
]
for cid, label, got, want in values:
    r.add(
        cid,
        f"표: {label} = {want}",
        0.1,
        got == want,
        "" if got == want else f"기대 {want!r}, 실제 {got!r}",
    )

# ③ 원인 절: 원인 배포 ID 정확히 하나만 등장 (전부 나열하는 산탄총 답을 막는다).
cause_ids = set(re.findall(r"deploy-\d+", section("원인")))
cause_ok = cause_ids == {CAUSE_DEPLOY}
r.add(
    "cause_id",
    f"원인 절의 배포 ID = {CAUSE_DEPLOY} 단독",
    0.15,
    cause_ok,
    "" if cause_ok else f"원인 절 배포 ID: {sorted(cause_ids)}",
)

# ④ 형식: 절 순서 + '| 지표 | 값 |' 헤더 표.
pos = [text.find(f"## {s}") for s in SECTIONS]
order_ok = all(p >= 0 for p in pos) and pos == sorted(pos)
header_ok = re.search(r"\|\s*지표\s*\|\s*값\s*\|", section("영향")) is not None
r.add(
    "format",
    "절 순서 준수 + 영향 절에 '| 지표 | 값 |' 표",
    0.1,
    bool(text) and order_ok and header_ok,
    "" if (order_ok and header_ok) else f"순서={order_ok}, 표 헤더={header_ok}",
)

r.emit()
