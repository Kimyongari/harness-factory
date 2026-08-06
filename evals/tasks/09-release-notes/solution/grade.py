"""채점: CHANGELOG.md 의 0.5.0 절만 절 단위 정규식으로 파싱해 포함/배제·분류·순서를 잰다.

문장 품질은 재지 않는다. 각 항목은 이슈번호 토큰(#N)으로 식별하고, 제외 대상은
이슈번호(revert 쌍)와 고유 키워드(chore/docs 커밋에만 나오는 단어)로 잡는다.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, workspace  # noqa: E402

# 포함돼야 하는 이슈 (commits.jsonl 의 feat/fix 중 revert 되지 않은 것)
BREAKING_ISSUES = {31, 44}  # body 에 BREAKING: 마커
ADDED_ISSUES = {12, 18, 23, 40, 47, 55, 62}
FIXED_ISSUES = {15, 19, 27, 34, 51, 58}
INCLUDED = BREAKING_ISSUES | ADDED_ISSUES | FIXED_ISSUES

# 제외돼야 하는 것: revert 쌍의 이슈 + chore/refactor/test/docs 커밋에만 등장하는 고유 키워드
REVERTED_ISSUES = {21, 29, 36}
FORBIDDEN_WORDS = [
    "revert",
    "pagination",
    "lockfile",
    "toolchain",
    "websocket",
    "quickstart",
    "proration",
    "middleware",
    "leap-year",
    "http/3",
]

ws = workspace()
r = Report()

text = ""
path = ws / "CHANGELOG.md"
if path.exists():
    text = path.read_text(encoding="utf-8", errors="ignore")


def section(body: str, heading_re: str, stop: str = r"^##\s") -> str | None:
    """절 하나를 같은 급의 다음 제목 직전까지 잘라 돌려준다."""
    m = re.search(rf"(?m)^{heading_re}[^\n]*\n(.*?)(?={stop}|\Z)", body, re.S)
    return m.group(0) if m else None


def has_issue(chunk: str, n: int) -> bool:
    return re.search(rf"#{n}(?!\d)", chunk) is not None


def bullet_issues(chunk: str) -> list[int]:
    """항목 줄(- 로 시작)마다 첫 이슈번호를 순서대로 뽑는다."""
    out = []
    for line in chunk.splitlines():
        if line.lstrip().startswith("-"):
            m = re.search(r"#(\d+)", line)
            if m:
                out.append(int(m.group(1)))
    return out


block = section(text, r"##\s*\[0\.5\.0\]\s*-\s*2026-08-06") or ""

# ① gate: 0.5.0 절 존재. 없으면 요청한 산출물 자체가 없다.
r.add(
    "section_exists",
    "'## [0.5.0] - 2026-08-06' 절 존재",
    0.05,
    bool(block),
    "" if block else "0.5.0 절 없음",
    gate=True,
)

# ② 재현율: 포함 대상 15건이 이슈번호 토큰으로 전부 존재.
missing = sorted(n for n in INCLUDED if not has_issue(block, n))
r.add(
    "recall",
    "포함 대상 15건(feat/fix, revert 제외) 전부 존재",
    0.3,
    bool(block) and not missing,
    f"누락: {missing}" if missing else "",
)

# ③ 정밀도: revert 쌍·chore/refactor/test/docs 가 섞여 들지 않음.
leaked_issues = sorted(n for n in REVERTED_ISSUES if has_issue(block, n))
leaked_words = [w for w in FORBIDDEN_WORDS if w in block.lower()]
r.add(
    "precision",
    "제외 대상(revert 쌍·내부 변경·docs) 미포함",
    0.3,
    bool(block) and not leaked_issues and not leaked_words,
    f"이슈 유입: {leaked_issues}, 키워드 유입: {leaked_words}"
    if (leaked_issues or leaked_words)
    else "",
)

# ④ Breaking 분류: BREAKING 마커 커밋 2건이 Breaking 절에만 있다.
subsections = {
    name: section(block, rf"###\s*{name}", stop=r"^#{2,3}\s") or ""
    for name in ("Breaking", "Added", "Fixed")
}
breaking_set = set(bullet_issues(subsections["Breaking"]))
duplicated = sorted(
    n
    for n in BREAKING_ISSUES
    if has_issue(subsections["Added"], n) or has_issue(subsections["Fixed"], n)
)
breaking_ok = bool(block) and breaking_set == BREAKING_ISSUES and not duplicated
r.add(
    "breaking",
    "Breaking 절 = BREAKING 마커 2건, 원래 분류에서는 제거",
    0.2,
    breaking_ok,
    "" if breaking_ok else f"Breaking={sorted(breaking_set)}, Added/Fixed 중복={duplicated}",
)

# ⑤ 형식·순서: 하위 절 순서 + 절 안 이슈번호 오름차순 + 기존 0.4.0 절 보존.
positions = [block.find(f"### {name}") for name in ("Breaking", "Added", "Fixed")]
order_ok = all(p >= 0 for p in positions) and positions == sorted(positions)
sorted_ok = all(
    bullet_issues(subsections[name]) == sorted(bullet_issues(subsections[name]))
    for name in ("Breaking", "Added", "Fixed")
)
old = section(text, r"##\s*\[0\.4\.0\]") or ""
old_ok = bool(old) and all(has_issue(old, n) for n in (3, 5, 7, 9))
fmt_ok = bool(block) and order_ok and sorted_ok and old_ok
r.add(
    "format_order",
    "하위 절 순서·이슈번호 오름차순·0.4.0 절 보존",
    0.15,
    fmt_ok,
    "" if fmt_ok else f"순서={order_ok}, 정렬={sorted_ok}, 0.4.0 보존={old_ok}",
)

r.emit()
