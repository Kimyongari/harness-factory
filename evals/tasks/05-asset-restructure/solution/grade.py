"""채점: held-out manifest 로부터 기대 최종 트리를 독립 계산해 작업공간과 대조한다.

에이전트가 작업공간의 manifest·gen_assets.py 를 고쳤어도 영향받지 않도록 기대값은
held-out 사본에서만 만든다. 멱등성은 에이전트의 reorganize.py 를 subprocess 로
한 번 더 실행해 exit 0 + 트리 불변으로 직접 잰다 — 산출물(스크립트)이 곧 계약이다.
"""

import fnmatch
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, workspace  # noqa: E402

MANIFEST = json.loads(
    (Path(__file__).parent / "heldout" / "assets_manifest.json").read_text(encoding="utf-8")
)
IMG = re.compile(r"^img_(\d{8})_(.+)\.png$")
DOC = re.compile(r"^doc_(\d{8})_(.+)\.md$")
SKIP_DIRS = {".git", "_heldout", ".venv", "node_modules", "__pycache__"}


def valid_date(digits: str) -> bool:
    try:
        datetime.strptime(digits, "%Y%m%d")
        return True
    except ValueError:
        return False


def expected_tree() -> tuple[dict[str, str], set[str]]:
    """manifest → (assets/ 기준 상대경로 → 논리 id, 충돌 그룹에 속한 경로 집합)."""
    groups: dict[tuple[str, str], list[tuple[str, str]]] = {}  # (base, ext) 아님: 목적지 키
    tree: dict[str, str] = {}
    for name, content in sorted(MANIFEST.items()):
        m = IMG.match(name)
        if m and valid_date(m.group(1)):
            date, slug = m.group(1), m.group(2)
            key = (f"media/{date[:4]}/{date[4:6]}", slug, ".png")
            groups.setdefault(key, []).append((date, content))
            continue
        m = DOC.match(name)
        if m and valid_date(m.group(1)):
            date, slug = m.group(1), m.group(2)
            key = (f"docs/{date[:4]}", slug, ".md")
            groups.setdefault(key, []).append((date, content))
            continue
        if fnmatch.fnmatch(name, "tmp_*.tmp"):
            continue  # 삭제 대상 — 기대 트리에 없다
        tree[f"unsorted/{name}"] = content

    collision_paths: set[str] = set()
    for (base, slug, ext), items in groups.items():
        items.sort()  # 날짜 오름차순
        for i, (_, content) in enumerate(items):
            rel = f"{base}/{slug}{ext}" if i == 0 else f"{base}/{slug}-{i + 1}{ext}"
            tree[rel] = content
            if len(items) > 1:
                collision_paths.add(rel)
    return tree, collision_paths


def snapshot(assets: Path) -> dict[str, str]:
    """assets/ 아래 전체 파일의 상대경로 → 내용 해시."""
    out = {}
    if not assets.is_dir():
        return out
    for path in assets.rglob("*"):
        if path.is_file():
            out[str(path.relative_to(assets))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def workspace_files(ws: Path) -> list[Path]:
    return [
        p
        for p in ws.rglob("*")
        if p.is_file() and not any(part in SKIP_DIRS for part in p.parts)
    ]


ws = workspace()
r = Report()
assets = ws / "assets"
expected, collision_paths = expected_tree()

# ① gate — 최종 트리(경로 집합) 일치. 시작 상태(평평한 120개)에서는 반드시 실패한다.
actual_paths = set(snapshot(assets))
tree_ok = actual_paths == set(expected)
missing = sorted(set(expected) - actual_paths)[:5]
extra = sorted(actual_paths - set(expected))[:5]
r.add(
    "tree_match",
    "최종 트리가 규칙의 기대 경로 집합과 일치",
    0.3,
    tree_ok,
    "" if tree_ok else f"누락={missing} 잉여={extra}",
    gate=True,
)

# ② 무손실(fatal) — tmp 를 제외한 모든 논리 id 가 작업공간 어딘가에 살아 있어야 한다.
#    잘못된 위치는 ①이 잡는다. fatal 은 내용 소멸(덮어쓰기·삭제)에만 쓴다.
#    baseline 에서는 원래 자리에 그대로 있으므로 통과한다.
contents: dict[str, int] = {}
for path in workspace_files(ws):
    try:
        text = path.read_text(encoding="utf-8").strip()
    except (UnicodeDecodeError, OSError):
        continue
    if text in contents:
        contents[text] += 1
    else:
        contents[text] = 1
keep_ids = {v for k, v in MANIFEST.items() if not fnmatch.fnmatch(k, "tmp_*.tmp")}
lost = sorted(i for i in keep_ids if contents.get(i, 0) == 0)
r.add(
    "no_content_loss",
    "모든 자산 내용(논리 id)이 소실 없이 보존",
    0.2,
    not lost,
    "" if not lost else f"소실된 id={lost[:6]}",
    fatal=True,
)

# ③ tmp 정리 — tmp_*.tmp 파일명도, 그 내용(orphan id)도 남아 있으면 안 된다.
tmp_files = [
    str(p.relative_to(ws))
    for p in workspace_files(ws)
    if fnmatch.fnmatch(p.name, "tmp_*.tmp")
]
orphan_ids = {v for k, v in MANIFEST.items() if fnmatch.fnmatch(k, "tmp_*.tmp")}
orphan_alive = sorted(i for i in orphan_ids if contents.get(i, 0) > 0)
tmp_ok = not tmp_files and not orphan_alive
r.add(
    "tmp_deleted",
    "고아 임시 파일(tmp_*.tmp) 삭제 완료",
    0.1,
    tmp_ok,
    "" if tmp_ok else f"잔존 파일={tmp_files[:4]} 잔존 내용={orphan_alive[:4]}",
)

# ④ 멱등성 — 에이전트의 reorganize.py 를 직접 한 번 더 실행: exit 0 + 트리 불변.
#    작업공간 **사본**에서 돌린다. 비멱등 스크립트의 재실행이 작업공간을 훼손하면
#    이후 항목과 재채점이 오염되기 때문이다.
script = ws / "reorganize.py"
if not script.exists():
    r.add("idempotent", "reorganize.py 재실행이 무해(멱등)", 0.25, False, "reorganize.py 없음")
else:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for src in workspace_files(ws):
            dest = tmp / src.relative_to(ws)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
        before = snapshot(tmp / "assets")
        try:
            proc = subprocess.run(
                [sys.executable, "reorganize.py"],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=60,
            )
            after = snapshot(tmp / "assets")
            idem = proc.returncode == 0 and after == before
            detail = (
                ""
                if idem
                else (
                    f"exit={proc.returncode} 트리변화={after != before} "
                    f"stderr={(proc.stderr or proc.stdout)[-300:]}"
                )
            )
        except subprocess.TimeoutExpired:
            idem, detail = False, "재실행 timeout"
    r.add("idempotent", "reorganize.py 재실행이 무해(멱등)", 0.25, idem, detail)

# ⑤ 충돌 접미사 — 충돌 그룹 경로들의 내용이 날짜 오름차순 매핑과 정확히 일치.
bad = []
for rel in sorted(collision_paths):
    path = assets / rel
    got = path.read_text(encoding="utf-8").strip() if path.is_file() else None
    if got != expected[rel]:
        bad.append(f"{rel}: 기대={expected[rel]} 실제={got}")
r.add(
    "collision_suffix",
    "충돌 접미사(-2, -3)가 날짜 오름차순으로 정확",
    0.15,
    not bad,
    "; ".join(bad[:4]),
)

r.emit()
