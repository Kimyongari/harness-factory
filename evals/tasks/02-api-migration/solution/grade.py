"""채점: 이전 완료(gate) → quirk 두 경로의 동작 보존 → 회귀.

에이전트가 test_app.py 를 어떻게 고쳤든 무관하게, held-out 사본이 원 사양의
동작을 판정한다. gate 는 "이전을 했는가"(legacy 삭제 + import 잔존 없음 +
보이는 동작 유지)이고, 점수의 몸통은 보이는 테스트가 덮지 않는 quirk 경로다.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, run_heldout, workspace  # noqa: E402

HELDOUT = Path(__file__).parent / "heldout"
ws = workspace()
r = Report()

# ---- gate: legacy.py 삭제 + legacy import 잔존 없음 + 보이는 동작 유지 --------
legacy_gone = not (ws / "config" / "legacy.py").exists()

IMPORT_RE = re.compile(
    r"(?:from\s+config\.legacy\s+import|import\s+config\.legacy\b"
    r"|from\s+config\s+import\s+(?:[\w\s,]*,\s*)?legacy\b)"
)
leftover_imports: list[str] = []
for path in ws.rglob("*.py"):
    if any(p in (".git", "_heldout", ".venv", "node_modules", "__pycache__") for p in path.parts):
        continue
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue
    if IMPORT_RE.search(text):
        leftover_imports.append(str(path.relative_to(ws)))

ok_gate, log = run_heldout(ws, HELDOUT, expr="gate")
detail = []
if not legacy_gone:
    detail.append("config/legacy.py 가 남아 있음")
if leftover_imports:
    detail.append(f"legacy import 잔존: {leftover_imports}")
if not ok_gate:
    detail.append(log)
r.add(
    "migrated",
    "legacy.py 삭제 + import 잔존 없음 + 보이는 동작 유지",
    0.25,
    legacy_gone and not leftover_imports and ok_gate,
    "; ".join(detail),
    gate=True,
)

# ---- quirk ①: 존재-truthiness — 명시된 0 값이 기본값으로 바뀌지 않았는가 ------
ok, log = run_heldout(ws, HELDOUT, expr="falsy")
r.add("falsy_path", "명시된 0 설정 유지(존재-truthiness quirk)", 0.3, ok, log if not ok else "")

# ---- quirk ②: str 전제 — 타입 보존 API 로 바꿔도 문자열 조립이 사는가 ---------
ok, log = run_heldout(ws, HELDOUT, expr="typed")
r.add("typed_path", "str 전제 조립 경로 유지(타입 quirk)", 0.3, ok, log if not ok else "")

# ---- 회귀: 키 부재 기본값·공개 반환 타입 --------------------------------------
ok, log = run_heldout(ws, HELDOUT, expr="regression")
r.add("no_regression", "키 부재 기본값·반환 타입 회귀 없음", 0.15, ok, log if not ok else "")

r.emit()
