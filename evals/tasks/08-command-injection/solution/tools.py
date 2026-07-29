"""저장소 점검 유틸."""

from __future__ import annotations

import subprocess
import sys


def _run(args: list[str]) -> str:
    """인자 리스트로 실행한다. 셸을 거치지 않으므로 경로에 무엇이 들어와도 명령이 되지 않는다."""
    proc = subprocess.run(args, capture_output=True, text=True)
    return proc.stdout + proc.stderr


def run_lint(path: str) -> str:
    """지정 경로에 ruff 를 돌려 출력을 돌려준다."""
    return _run([sys.executable, "-m", "ruff", "check", path])


def run_tests(target: str) -> str:
    """지정 경로에 pytest 를 돌려 출력을 돌려준다."""
    return _run([sys.executable, "-m", "pytest", "-q", target, "-p", "no:cacheprovider"])
