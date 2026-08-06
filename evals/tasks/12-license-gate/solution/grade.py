"""채점: 작업공간의 check_licenses.py 를 held-out 픽스처로 subprocess 실행해
출력·exit code 를 골든 산출 기대값(.expected.tsv)과 대조한다."""

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, workspace  # noqa: E402

HELDOUT = Path(__file__).parent / "heldout"
ws = workspace()
r = Report()

CLI = ws / "check_licenses.py"


def run_cli(stem: str):
    return subprocess.run(
        [sys.executable, str(CLI), str(HELDOUT / f"{stem}.json")],
        cwd=ws,
        capture_output=True,
        text=True,
        timeout=60,
    )


def expected(stem: str) -> tuple[int, list[str]]:
    lines = (HELDOUT / f"{stem}.expected.tsv").read_text(encoding="utf-8").splitlines()
    return int(lines[0].removeprefix("exit=")), lines[1:]


def matches(stem: str, check_exit: bool = True) -> tuple[bool, str]:
    if not CLI.exists():
        return False, "check_licenses.py 없음"
    try:
        proc = run_cli(stem)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    want_exit, want_lines = expected(stem)
    got_lines = proc.stdout.splitlines()
    if got_lines != want_lines:
        diff = [
            f"want={w!r} got={g!r}" for w, g in zip(want_lines, got_lines, strict=False) if w != g
        ]
        if len(got_lines) != len(want_lines):
            diff.append(f"줄 수 {len(got_lines)} != {len(want_lines)}")
        return False, f"{stem}: " + "; ".join(diff[:5])
    if check_exit and proc.returncode != want_exit:
        return False, f"{stem}: exit={proc.returncode} != {want_exit}"
    return True, ""


# 게이트: 보이는 테스트 수준의 단일 식별자 4종(allow/forbidden/conditional/unknown).
ok, detail = matches("basic")
r.add("gate_basic", "CLI 기본 동작(단일 식별자 4종)", 0.15, ok, detail, gate=True)

# 그룹 ①: 중첩 괄호 × OR/AND 혼합.
ok, detail = matches("nested")
r.add("nested_expr", "중첩 괄호·OR/AND 혼합 판정", 0.20, ok, detail)

# 그룹 ②: WITH 의미론 · 괄호 없는 결합 우선순위(WITH > AND > OR).
ok, detail = matches("withprec")
r.add("with_precedence", "WITH 의미론·결합 우선순위", 0.20, ok, detail)

# 그룹 ③: 대소문자·공백 관용, 파싱 불가→unknown, deny 사유 우선순위.
ok, detail = matches("lexical")
r.add("lexical_edges", "대소문자·공백·파싱 오류·사유 우선순위", 0.15, ok, detail)

# exit code 계약: 전부 allow 면 0, 하나라도 deny 면 1.
if CLI.exists():
    try:
        exit_ok = run_cli("allow_all").returncode == 0 and run_cli("one_deny").returncode == 1
        exit_detail = "" if exit_ok else "allow_all→0 / one_deny→1 이 아님"
    except subprocess.TimeoutExpired:
        exit_ok, exit_detail = False, "timeout"
else:
    exit_ok, exit_detail = False, "check_licenses.py 없음"
r.add("exit_code", "exit code 계약(deny 존재 여부)", 0.15, exit_ok, exit_detail)

# 출력 형식·정렬: 3필드 TAB 구분, 판정·사유 어휘 준수, 이름 오름차순(코드포인트).
_LINE = re.compile(r"^[^\t]+\t(allow|deny)\t(ok|forbidden|conditional|unknown)$")
if CLI.exists():
    try:
        proc = run_cli("format")
        lines = proc.stdout.splitlines()
        names = [line.split("\t")[0] for line in lines]
        fixture_names = sorted(
            str(p["name"]) for p in json.loads((HELDOUT / "format.json").read_text("utf-8"))
        )
        fmt_ok = bool(lines) and all(_LINE.match(line) for line in lines) and names == fixture_names
        fmt_detail = "" if fmt_ok else f"lines={lines[:6]}"
    except subprocess.TimeoutExpired:
        fmt_ok, fmt_detail = False, "timeout"
else:
    fmt_ok, fmt_detail = False, "check_licenses.py 없음"
r.add("output_format", "출력 형식·이름 정렬", 0.15, fmt_ok, fmt_detail)

r.emit()
