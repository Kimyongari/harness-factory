"""보이는 테스트 — 단일 식별자·기본 계약만 덮는 쉬운 케이스."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SCRIPT = ROOT / "check_licenses.py"


def run_cli(packages, tmp_path):
    fixture = tmp_path / "deps.json"
    fixture.write_text(json.dumps(packages), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(fixture)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_allow_simple(tmp_path):
    proc = run_cli([{"name": "a", "license": "MIT"}], tmp_path)
    assert proc.stdout.splitlines() == ["a\tallow\tok"]
    assert proc.returncode == 0


def test_deny_forbidden(tmp_path):
    proc = run_cli([{"name": "b", "license": "GPL-3.0-only"}], tmp_path)
    assert proc.stdout.splitlines() == ["b\tdeny\tforbidden"]
    assert proc.returncode == 1


def test_deny_conditional_lgpl(tmp_path):
    proc = run_cli([{"name": "c", "license": "LGPL-2.1-only"}], tmp_path)
    assert proc.stdout.splitlines() == ["c\tdeny\tconditional"]
    assert proc.returncode == 1


def test_deny_unknown(tmp_path):
    proc = run_cli([{"name": "d", "license": "WTFPL"}], tmp_path)
    assert proc.stdout.splitlines() == ["d\tdeny\tunknown"]
    assert proc.returncode == 1


def test_sorted_output_on_project_deps(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(ROOT / "deps.json")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    lines = proc.stdout.splitlines()
    names = [line.split("\t")[0] for line in lines]
    assert len(lines) == 25
    assert names == sorted(names)
    assert proc.returncode == 1  # GPL 의존성이 있으므로
