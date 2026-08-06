"""채점: report.json 을 하드코딩 기대값과 완전 일치로 대조하고, build_report.py 를
작업공간 사본에서 재실행해 같은 report 가 재생성되는지 본다.

기대값의 출처: heldout/gen_fixtures.py — 픽스처를 만든 행 모델(Decimal)에서 직접 계산한
값이라 파서 구현과 독립이다. 픽스처를 바꾸면 그 스크립트를 다시 돌려 아래 상수를 갱신한다.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, workspace  # noqa: E402

EXPECTED = {
    "total_revenue_cents": 3683515,
    "refund_cents": 250343,
    "net_cents": 3433172,
    "by_product": {
        "USB-C 허브": 1114988,
        "Webcam Pro": 312592,
        "게이밍 마우스": 726109,
        "노트북 스탠드": 392435,
        "모니터암": 488807,
        "무선 키보드": 648584,
    },
    "duplicates_dropped": 5,
    "conflicts_resolved": 2,
}
KEYS = set(EXPECTED)
INT_KEYS = ["total_revenue_cents", "refund_cents", "net_cents", "duplicates_dropped", "conflicts_resolved"]

ws = workspace()
r = Report()


def is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def load_report(path: Path):
    """(dict|None, 오류설명). 스키마 위반은 이유를 남긴다."""
    if not path.exists():
        return None, "report.json 없음"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        return None, f"JSON 파싱 실패: {e}"
    if not isinstance(data, dict):
        return None, "최상위가 객체가 아님"
    if set(data) != KEYS:
        return None, f"키 불일치: {sorted(data)}"
    if not all(is_int(data[k]) for k in INT_KEYS):
        return None, "정수여야 할 필드가 정수가 아님"
    bp = data["by_product"]
    if not isinstance(bp, dict) or not all(isinstance(k, str) and is_int(v) for k, v in bp.items()):
        return None, "by_product 는 {str: int} 여야 함"
    return data, ""


report, why = load_report(ws / "report.json")

# 게이트: 산출물 계약(파일 존재 + 키 6개 + 타입). 이걸 못 지키면 나머지는 볼 것도 없다.
r.add("schema", "report.json 존재·스키마(키 6개·정수 타입)", 0.15, report is not None, why, gate=True)

# 수치 완전 일치 — Decimal 기반 half-away 반올림·cp949·괄호 표기·충돌 해소가 전부 맞아야 한다.
totals_ok = report is not None and all(report[k] == EXPECTED[k] for k in INT_KEYS[:3])
r.add(
    "totals",
    "total/refund/net 정수 센트 완전 일치",
    0.3,
    totals_ok,
    ""
    if totals_ok
    else f"got={ {k: report[k] for k in INT_KEYS[:3]} if report else None }",
)

bp_ok = report is not None and report["by_product"] == EXPECTED["by_product"]
r.add(
    "by_product",
    "제품별 집계 완전 일치(제품명 원문 키)",
    0.25,
    bp_ok,
    "" if bp_ok else f"got={report['by_product'] if report else None}",
)

counts_ok = (
    report is not None
    and report["duplicates_dropped"] == EXPECTED["duplicates_dropped"]
    and report["conflicts_resolved"] == EXPECTED["conflicts_resolved"]
)
r.add(
    "counts",
    "중복 5건·충돌 2건 카운트",
    0.15,
    counts_ok,
    ""
    if counts_ok
    else f"got={(report['duplicates_dropped'], report['conflicts_resolved']) if report else None}",
)


def reproduces() -> tuple[bool, str]:
    """작업공간 사본(report.json 제외)에서 build_report.py 를 돌려 같은 report 가 나오는가."""
    if report is None:
        return False, "대조할 report.json 이 없음"
    if not (ws / "build_report.py").exists():
        return False, "build_report.py 없음"
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for src in ws.rglob("*"):
            rel = src.relative_to(ws)
            if any(part in (".git", "_heldout", "__pycache__") for part in rel.parts):
                continue
            if rel.as_posix() == "report.json":
                continue  # 재생성 대상 — 사본에는 없어야 '재생성' 이다
            if src.is_file():
                (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, tmp / rel)
        try:
            proc = subprocess.run(
                [sys.executable, "build_report.py"],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            return False, "build_report.py 타임아웃"
        if proc.returncode != 0:
            return False, f"exit={proc.returncode}: {(proc.stderr or proc.stdout)[-300:]}"
        regen, why2 = load_report(tmp / "report.json")
        if regen is None:
            return False, f"재생성 실패: {why2}"
        return regen == report, "" if regen == report else "재생성 결과가 report.json 과 다름"


ok, detail = reproduces()
r.add("reproduce", "build_report.py 재실행이 같은 report.json 재생성", 0.15, ok, detail)

r.emit()
