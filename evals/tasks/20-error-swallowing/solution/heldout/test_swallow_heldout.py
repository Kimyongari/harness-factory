"""held-out: 계속 처리하는지 + 실패가 관찰 가능한지 + 중단 신호가 살아 있는지."""

import importlib
import logging
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GOOD = [{"id": 1, "name": " Alice "}, {"id": 3, "name": "CAROL"}]
BAD = {"id": 2}  # name 없음 → KeyError


def _pipeline():
    sys.modules.pop("pipeline", None)
    return importlib.import_module("pipeline")


def test_continues_on_error():
    pipeline = _pipeline()
    out = pipeline.process([GOOD[0], BAD, GOOD[1]])
    names = [row["name"] for row in out if isinstance(row, dict) and "name" in row]
    assert "alice" in names and "carol" in names, f"정상 항목이 처리되지 않았다: {out}"


def test_failure_is_observable(capsys, caplog):
    """실패 항목을 어디서든 알 수 있어야 한다 — 반환값·로그·표준출력 중 하나."""
    pipeline = _pipeline()
    with caplog.at_level(logging.DEBUG):
        out = pipeline.process([GOOD[0], BAD, GOOD[1]])
    captured = capsys.readouterr()
    surface = captured.out + captured.err + caplog.text + repr(out) + repr(getattr(out, "failures", ""))
    for attr in ("failures", "errors", "failed", "skipped"):
        surface += repr(getattr(pipeline, attr, ""))
    assert "2" in surface or "KeyError" in surface or "name" in surface.replace("name'", ""), (
        f"실패가 조용히 삼켜졌다 — 어디에도 흔적이 없다: {surface[:300]!r}"
    )


def test_interrupt_not_swallowed():
    """bare except 로 KeyboardInterrupt 까지 잡으면 중단할 수 없는 루프가 된다."""
    pipeline = _pipeline()

    def boom(item):
        raise KeyboardInterrupt("사용자 중단")

    pipeline.transform = boom
    with pytest.raises(KeyboardInterrupt):
        pipeline.process(GOOD)


def test_pass_to_pass():
    pipeline = _pipeline()
    out = pipeline.process(GOOD)
    assert [row["name"] for row in out] == ["alice", "carol"]
