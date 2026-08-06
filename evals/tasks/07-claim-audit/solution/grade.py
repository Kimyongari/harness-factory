"""채점: audit.json 의 판정과 **증거 실재**를 대조한다.

verdict 는 정답표와 비교하고, evidence 는 주장별 허용 목록(파일 + 그 줄이 매칭해야
할 정규식)으로 검증한다. 인용된 file:line 은 에이전트 작업공간이 아니라 pristine
project/ 에서 연다 — 소스를 고쳐 증거를 "만드는" 조작을 무력화한다(감사는 읽기 작업).
존재하지 않는 파일·줄 인용(지어낸 근거)이 하나라도 있으면 evidence 전 항목 0 이다.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, workspace  # noqa: E402

PROJECT = Path(__file__).resolve().parents[1] / "project"

VERDICTS = {
    1: True,
    2: False,  # docstring 은 5회, 코드는 range(RETRY_LIMIT)=3회
    3: True,
    4: False,  # CACHE_TTL 이 초가 아니라 분 단위(ttl * 60)
    5: True,
    6: False,  # create_dispatcher 가 폴백 "DEBUG" 로 오버라이드
    7: True,
    8: False,  # 예외를 재던지지 않고 로깅 후 None 반환(삼킴)
    9: True,
    10: True,
}

# 주장별 허용 증거: (파일, 인용 줄 ±1 안에서 매칭해야 할 정규식). 여러 줄이 정당할 수
# 있는 주장은 대안을 나란히 둔다.
EVIDENCE = {
    1: [
        ("src/config.py", r"BATCH_SIZE\s*=\s*50"),
        ("src/dispatcher.py", r"range\(0,\s*len\(pending\),\s*config\.BATCH_SIZE\)"),
    ],
    2: [
        ("src/config.py", r"RETRY_LIMIT\s*=\s*3"),
        ("src/transport.py", r"for attempt in range\(config\.RETRY_LIMIT\)"),
    ],
    3: [("src/transport.py", r"sleep\(2\s*\*\*\s*attempt\)")],
    4: [("src/cache.py", r"ttl\s*\*\s*60")],
    5: [("src/dispatcher.py", r"_seen\.get\(message\.dedupe_key\)")],
    6: [("src/dispatcher.py", r"NOTIFY_LOG_LEVEL.{0,5}\s*\"DEBUG\"")],
    7: [("src/dispatcher.py", r"if message is None")],
    8: [("src/parsers.py", r"return None")],
    9: [("src/dispatcher.py", r"_seen\.set\(message\.dedupe_key")],
    10: [("src/dispatcher.py", r"sorted\(results,\s*key=lambda r: r\.message_id\)")],
}

ws = workspace()
r = Report()


def fail_all(reason: str) -> None:
    r.add(
        "audit_schema", "audit.json 존재 + 스키마(주장 10개 전부)", 0.05, False, reason, gate=True
    )
    r.add("format", "형식: claim 오름차순 정렬 + 타입", 0.10, False, "미평가")
    for c in range(1, 11):
        r.add(f"verdict_{c}", f"주장 {c} 판정", 0.05, False, "미평가")
        r.add(f"evidence_{c}", f"주장 {c} 증거", 0.035, False, "미평가")
    r.emit()
    raise SystemExit(0)


audit_path = ws / "audit.json"
if not audit_path.exists():
    fail_all("audit.json 없음")
try:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
except (ValueError, UnicodeDecodeError) as exc:
    fail_all(f"JSON 파싱 실패: {exc}")

# ── gate: 스키마 — 배열, 원소 10개, claim 1..10 각 1회, verdict/evidence 키 존재.
entries: dict[int, dict] = {}
schema_ok = isinstance(audit, list) and len(audit) == 10
if schema_ok:
    for item in audit:
        if not isinstance(item, dict) or not isinstance(item.get("claim"), int):
            schema_ok = False
            break
        if "verdict" not in item or not isinstance(item.get("evidence"), dict):
            schema_ok = False
            break
        if not {"file", "line"} <= item["evidence"].keys():
            schema_ok = False
            break
        entries[item["claim"]] = item
    schema_ok = schema_ok and set(entries) == set(range(1, 11))
if not schema_ok:
    fail_all("스키마 위반(배열 10원소·claim 1..10·verdict·evidence.file/line)")
r.add("audit_schema", "audit.json 존재 + 스키마(주장 10개 전부)", 0.05, True, gate=True)

# ── 형식: 오름차순 정렬 + 엄격 타입(verdict bool, line 양의 int, file str).
ordered = [item["claim"] for item in audit] == list(range(1, 11))
typed = all(
    isinstance(e["verdict"], bool)
    and isinstance(e["evidence"]["file"], str)
    and isinstance(e["evidence"]["line"], int)
    and not isinstance(e["evidence"]["line"], bool)
    and e["evidence"]["line"] >= 1
    for e in entries.values()
)
r.add(
    "format",
    "형식: claim 오름차순 정렬 + 타입",
    0.10,
    ordered and typed,
    "" if ordered and typed else f"정렬={ordered}, 타입={typed}",
)


def resolve_evidence(ev: dict) -> tuple[str, str, list[str], int]:
    """(status, 정규화 경로, 파일 줄 목록, line). status: ok|malformed|fabricated."""
    file, line = ev.get("file"), ev.get("line")
    if not isinstance(file, str) or isinstance(line, bool) or not isinstance(line, int):
        return "malformed", "", [], 0
    rel = file[2:] if file.startswith("./") else file
    path = (PROJECT / rel).resolve()
    if not str(path).startswith(str(PROJECT.resolve())) or not path.is_file():
        return "fabricated", rel, [], line
    lines = path.read_text(encoding="utf-8").splitlines()
    if line < 1 or line > len(lines):
        return "fabricated", rel, lines, line
    return "ok", rel, lines, line


resolved = {c: resolve_evidence(entries[c]["evidence"]) for c in range(1, 11)}
fabricated = [c for c, (status, *_rest) in resolved.items() if status == "fabricated"]

for c in range(1, 11):
    entry = entries[c]
    verdict_ok = entry["verdict"] is VERDICTS[c]
    r.add(
        f"verdict_{c}",
        f"주장 {c} 판정({'참' if VERDICTS[c] else '거짓'})",
        0.05,
        verdict_ok,
        "" if verdict_ok else f"제출={entry['verdict']!r}",
    )

    status, rel, lines, line = resolved[c]
    if fabricated:
        ev_ok, detail = False, f"지어낸 근거 존재(주장 {fabricated}) → evidence 전 항목 0"
    elif status != "ok":
        ev_ok, detail = False, f"증거 참조 불량({status}): {entry['evidence']!r}"
    elif not verdict_ok:
        ev_ok, detail = False, "판정이 틀려 증거 불인정"
    else:
        window = lines[max(0, line - 2) : line + 1]  # 인용 줄 ±1
        ev_ok = any(rel == f and any(re.search(rx, ln) for ln in window) for f, rx in EVIDENCE[c])
        detail = "" if ev_ok else f"{rel}:{line} 은 허용 증거와 불일치"
    r.add(f"evidence_{c}", f"주장 {c} 증거(file:line 실재+내용 대조)", 0.035, ev_ok, detail)

r.emit()
