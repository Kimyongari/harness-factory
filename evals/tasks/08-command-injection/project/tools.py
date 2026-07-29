"""저장소 점검 유틸."""

from __future__ import annotations

import subprocess


def run_lint(path: str) -> str:
    """지정 경로에 ruff 를 돌려 출력을 돌려준다."""
    proc = subprocess.run(
        f"ruff check {path}", shell=True, capture_output=True, text=True
    )
    return proc.stdout + proc.stderr
