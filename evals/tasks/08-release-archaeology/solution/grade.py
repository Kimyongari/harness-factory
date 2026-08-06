"""채점: answers.json 의 답과 **증거 실재**를 대조한다.

답은 정답표와 비교하고, evidence 는 질문별 허용 목록(파일 + 그 줄이 매칭해야 할
정규식)으로 검증한다. 인용된 file:line 은 에이전트 작업공간이 아니라 pristine
project/ 에서 연다(조사는 읽기 작업 — 소스를 고쳐 증거를 만드는 조작을 무력화).
존재하지 않는 파일·줄 인용(지어낸 근거)이 하나라도 있으면 evidence 전 항목 0 이다.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, workspace  # noqa: E402

PROJECT = Path(__file__).resolve().parents[1] / "project"
VERSION_RE = re.compile(r"^v0\.[1-9]$")

Q1 = "v0.5"  # check 반환 타입 bool → dict
Q2_INTRODUCED = "v0.3"  # remaining 의 max(0, …) 클램프 소실
Q2_FIXED = "v0.8"  # 클램프 복원
Q3 = "v0.6"  # "동작 변화 없음" 이라지만 _normalize 로 키 의미가 변함
Q4 = [("v0.1", 60), ("v0.4", 30), ("v0.7", 45)]

# 질문별 허용 증거: (파일, 인용 줄 ±1 안에서 매칭해야 할 정규식).
EV_Q1 = [
    ("releases/v0.5/limiter.py", r"def check\(self, key: str\) -> dict:"),
    ("releases/v0.5/limiter.py", r"return \{\"allowed\": allowed, \"remaining\": self\.remaining\(key\)\}"),
]
EV_Q2_INTRODUCED = [("releases/v0.3/limiter.py", r"return self\.limit - bucket\.count")]
EV_Q2_FIXED = [("releases/v0.8/limiter.py", r"return max\(0, self\.limit - window_bucket\.count\)")]
EV_Q3 = [
    ("releases/v0.6/limiter.py", r"key\.strip\(\)\.lower\(\)"),
    ("releases/v0.6/limiter.py", r"_normalize\(key\)"),
]
EV_Q4 = {
    "v0.1": [("releases/v0.1/config.py", r"WINDOW_SECONDS\s*=\s*60\b")],
    "v0.4": [("releases/v0.4/config.py", r"WINDOW_SECONDS\s*=\s*30\b")],
    "v0.7": [("releases/v0.7/config.py", r"WINDOW_SECONDS\s*=\s*45\b")],
}

ITEMS = [
    ("q1_answer", "q1: check 반환 타입이 바뀐 첫 버전", 0.15),
    ("q2_introduced", "q2: 음수 remaining 버그 도입 버전", 0.075),
    ("q2_fixed", "q2: 음수 remaining 버그 수정 버전", 0.075),
    ("q3_answer", "q3: CHANGES.md 와 코드가 모순되는 버전", 0.15),
    ("q4_answer", "q4: WINDOW_SECONDS 변화 이력(버전→값)", 0.15),
    ("ev_q1", "q1 증거(file:line 실재+내용 대조)", 0.05),
    ("ev_q2_introduced", "q2 도입 증거", 0.05),
    ("ev_q2_fixed", "q2 수정 증거", 0.05),
    ("ev_q3", "q3 증거", 0.05),
    ("ev_q4", "q4 증거(항목별 대응)", 0.05),
]

ws = workspace()
r = Report()


def fail_all(reason: str) -> None:
    r.add("answers_schema", "answers.json 존재 + 스키마", 0.05, False, reason, gate=True)
    r.add("format", "형식: 버전 표기·정렬·타입", 0.10, False, "미평가")
    for cid, label, weight in ITEMS:
        r.add(cid, label, weight, False, "미평가")
    r.emit()
    raise SystemExit(0)


def is_ref(node) -> bool:
    return isinstance(node, dict) and {"file", "line"} <= node.keys()


answers_path = ws / "answers.json"
if not answers_path.exists():
    fail_all("answers.json 없음")
try:
    data = json.loads(answers_path.read_text(encoding="utf-8"))
except (ValueError, UnicodeDecodeError) as exc:
    fail_all(f"JSON 파싱 실패: {exc}")

schema_ok = (
    isinstance(data, dict)
    and isinstance(data.get("q1"), dict)
    and "answer" in data.get("q1", {})
    and is_ref(data["q1"].get("evidence"))
    and isinstance(data.get("q2"), dict)
    and {"introduced", "fixed", "evidence"} <= data.get("q2", {}).keys()
    and isinstance(data["q2"]["evidence"], dict)
    and is_ref(data["q2"]["evidence"].get("introduced"))
    and is_ref(data["q2"]["evidence"].get("fixed"))
    and isinstance(data.get("q3"), dict)
    and "answer" in data.get("q3", {})
    and is_ref(data["q3"].get("evidence"))
    and isinstance(data.get("q4"), dict)
    and isinstance(data.get("q4", {}).get("answer"), list)
    and isinstance(data.get("q4", {}).get("evidence"), list)
)
if not schema_ok:
    fail_all("스키마 위반(q1~q4·answer/evidence 구조)")
r.add("answers_schema", "answers.json 존재 + 스키마", 0.05, True, gate=True)

q1, q2, q3, q4 = data["q1"], data["q2"], data["q3"], data["q4"]

# ── 형식: 버전 표기 v0.X, q4 오름차순·타입, evidence 대응 길이.
versions = [q1.get("answer"), q2.get("introduced"), q2.get("fixed"), q3.get("answer")] + [
    e.get("version") for e in q4["answer"] if isinstance(e, dict)
]
version_ok = all(isinstance(v, str) and VERSION_RE.match(v) for v in versions)
q4_entries_ok = all(
    isinstance(e, dict)
    and {"version", "value"} <= e.keys()
    and isinstance(e.get("value"), int)
    and not isinstance(e.get("value"), bool)
    for e in q4["answer"]
)
q4_minors = [int(e["version"][3:]) for e in q4["answer"]] if version_ok and q4_entries_ok else []
q4_sorted = q4_minors == sorted(q4_minors)
q4_paired = len(q4["evidence"]) == len(q4["answer"])
format_ok = version_ok and q4_entries_ok and q4_sorted and q4_paired
r.add(
    "format",
    "형식: 버전 표기·정렬·타입",
    0.10,
    format_ok,
    ""
    if format_ok
    else f"버전표기={version_ok}, q4타입={q4_entries_ok}, q4정렬={q4_sorted}, q4대응={q4_paired}",
)


def resolve_ref(ev) -> tuple[str, str, list[str], int]:
    """(status, 정규화 경로, 파일 줄 목록, line). status: ok|malformed|fabricated."""
    if not isinstance(ev, dict):
        return "malformed", "", [], 0
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


refs = {
    "ev_q1": q1.get("evidence"),
    "ev_q2_introduced": q2["evidence"].get("introduced"),
    "ev_q2_fixed": q2["evidence"].get("fixed"),
    "ev_q3": q3.get("evidence"),
}
for i, ev in enumerate(q4["evidence"]):
    refs[f"ev_q4_{i}"] = ev
resolved = {key: resolve_ref(ev) for key, ev in refs.items()}
fabricated = sorted(key for key, (status, *_r) in resolved.items() if status == "fabricated")


def ev_pass(key: str, answer_ok: bool, allowed: list[tuple[str, str]]) -> tuple[bool, str]:
    if fabricated:
        return False, f"지어낸 근거 존재({fabricated}) → evidence 전 항목 0"
    status, rel, lines, line = resolved[key]
    if status != "ok":
        return False, f"증거 참조 불량({status})"
    if not answer_ok:
        return False, "답이 틀려 증거 불인정"
    window = lines[max(0, line - 2) : line + 1]  # 인용 줄 ±1
    if any(rel == f and any(re.search(rx, ln) for ln in window) for f, rx in allowed):
        return True, ""
    return False, f"{rel}:{line} 은 허용 증거와 불일치"


# ── 답 정확도.
q1_ok = q1.get("answer") == Q1
q2i_ok = q2.get("introduced") == Q2_INTRODUCED
q2f_ok = q2.get("fixed") == Q2_FIXED
q3_ok = q3.get("answer") == Q3
q4_given = [
    (e.get("version"), e.get("value")) for e in q4["answer"] if isinstance(e, dict)
]
q4_ok = q4_given == Q4

r.add("q1_answer", ITEMS[0][1], 0.15, q1_ok, "" if q1_ok else f"제출={q1.get('answer')!r}")
r.add("q2_introduced", ITEMS[1][1], 0.075, q2i_ok, "" if q2i_ok else f"제출={q2.get('introduced')!r}")
r.add("q2_fixed", ITEMS[2][1], 0.075, q2f_ok, "" if q2f_ok else f"제출={q2.get('fixed')!r}")
r.add("q3_answer", ITEMS[3][1], 0.15, q3_ok, "" if q3_ok else f"제출={q3.get('answer')!r}")
r.add("q4_answer", ITEMS[4][1], 0.15, q4_ok, "" if q4_ok else f"제출={q4_given!r}")

# ── 증거.
ok, detail = ev_pass("ev_q1", q1_ok, EV_Q1)
r.add("ev_q1", ITEMS[5][1], 0.05, ok, detail)
ok, detail = ev_pass("ev_q2_introduced", q2i_ok, EV_Q2_INTRODUCED)
r.add("ev_q2_introduced", ITEMS[6][1], 0.05, ok, detail)
ok, detail = ev_pass("ev_q2_fixed", q2f_ok, EV_Q2_FIXED)
r.add("ev_q2_fixed", ITEMS[7][1], 0.05, ok, detail)
ok, detail = ev_pass("ev_q3", q3_ok, EV_Q3)
r.add("ev_q3", ITEMS[8][1], 0.05, ok, detail)

if q4_ok and len(q4["evidence"]) == len(Q4):
    parts = [
        ev_pass(f"ev_q4_{i}", True, EV_Q4[version]) for i, (version, _value) in enumerate(Q4)
    ]
    q4_ev_ok = all(ok for ok, _d in parts)
    q4_detail = "" if q4_ev_ok else "; ".join(d for _ok, d in parts if d)
else:
    q4_ev_ok, q4_detail = False, "답이 틀리거나 evidence 대응 길이 불일치"
r.add("ev_q4", ITEMS[9][1], 0.05, q4_ev_ok, q4_detail)

r.emit()
