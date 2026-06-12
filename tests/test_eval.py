"""생성 하네스 eval — 경량 모드는 CI 에서 항상 돈다(LLM 없음).

test_engine.py 가 산출물의 *모양*을 보는 단위테스트라면, 여기서는 산출물을 임시
프로젝트에 깔아 *행동*을 검증한다:
  - guard-bash 가 위반 명령을 실제로 deny / benign 은 통과
  - verify.sh Stop 게이트가 망가진 상태를 막고 골든 수정 후엔 통과

전체(full) 모드(실제 claude -p 구동)는 비싸므로 HARNESS_EVAL_FULL=1 + CLI 가 있을 때만 돈다.
"""

import tempfile
from pathlib import Path

import pytest

from evals import harness


# ----------------------------------------------------- (b) guard-bash 차단 정확도
@pytest.fixture(scope="module")
def harness_dir():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        harness.materialize_harness(d)
        yield d


@pytest.mark.parametrize("case", harness.GUARD_CASES, ids=lambda c: c.name)
def test_guard_bash_blocks_violations(harness_dir, case):
    """rm -rf / force push / never_touch 스테이징 / 파이프-투-셸 은 차단, benign 은 통과해야 한다."""
    blocked = harness.run_guard(harness_dir, case.command)
    assert blocked == case.expect_block, (
        f"{case.name!r}: 차단={blocked}, 기대={case.expect_block} (명령: {case.command})"
    )


# --------------------------------------------- (c) verify.sh Stop 게이트
@pytest.mark.parametrize("task", harness.load_tasks(), ids=lambda t: t.id)
def test_verify_blocks_broken_state(task):
    """망가진 골든 프로젝트에서는 verify.sh 가 non-zero 로 미완성 작업을 막아야 한다."""
    with tempfile.TemporaryDirectory() as tmp:
        proj = harness.setup_task_workspace(task, Path(tmp))
        result = harness.run_verify(proj)
        assert not result.passed, f"[{task.id}] 망가진 상태인데 verify 가 통과함:\n{result.output}"


@pytest.mark.parametrize("task", harness.load_tasks(), ids=lambda t: t.id)
def test_verify_passes_after_golden_fix(task):
    """골든 수정을 적용하면 verify.sh 가 통과해야 한다(골든패스가 실제로 도달 가능함)."""
    with tempfile.TemporaryDirectory() as tmp:
        proj = harness.setup_task_workspace(task, Path(tmp))
        harness.apply_solution(task, proj)
        result = harness.run_verify(proj)
        assert result.passed, f"[{task.id}] 골든 수정 후에도 verify 실패:\n{result.output}"


# ----------------------------------------------- (a) 전체 모드: 골든패스 통과율
_full_active, _full_reason = harness.full_mode_status()


@pytest.mark.skipif(not _full_active, reason=_full_reason)
@pytest.mark.parametrize("task", harness.load_tasks(), ids=lambda t: t.id)
def test_agent_solves_golden_task(task):
    """실제 에이전트가 태스크 프롬프트만 받고 풀어 verify.sh 를 통과시키는가(골든패스)."""
    with tempfile.TemporaryDirectory() as tmp:
        proj = harness.setup_task_workspace(task, Path(tmp))
        harness.run_agent(task.prompt, proj)
        result = harness.run_verify(proj)
        assert result.passed, f"[{task.id}] 에이전트 작업 후 verify 실패:\n{result.output}"
