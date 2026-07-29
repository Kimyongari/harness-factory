"""eval 스위트 자체를 검증하는 테스트 — LLM 없이 돌기 때문에 CI 에서 항상 돈다.

`test_engine.py` 가 생성기 산출물의 *모양*을 보는 단위테스트라면, 여기서는

  (1) 생성된 PreToolUse 가드가 위반 명령을 실제로 **차단**하는가 (행동)
  (2) A/B 채점기가 **정답을 인정하고 미수행을 걸러내며 조건 편향이 없는가** (채점기의 채점)

를 본다. (2)가 깨진 상태의 A/B 결과는 신뢰할 수 없으므로, 실제 에이전트 실행을 CI 에 넣는 대신
이 자기검증을 게이트로 둔다. 실제 A/B 실행은 `python -m evals.abrun --mode agent`.
"""

import tempfile
from pathlib import Path

import pytest

from evals import harness, run
from evals.abrun import CONDITIONS, apply_golden, load_tasks, prepare

TASKS = load_tasks(None)


# ----------------------------------------------------- (1) guard-bash 차단 정확도
@pytest.fixture(scope="module")
def harness_dir():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        harness.materialize_harness(d)
        for path in d.glob(".scripts/*.sh"):
            path.chmod(0o755)
        yield d


@pytest.mark.parametrize("case", harness.GUARD_CASES, ids=lambda c: c.name)
def test_guard_bash_blocks_violations(harness_dir, case):
    """rm -rf / force push / never_touch 스테이징 / 파이프-투-셸 은 차단, benign 은 통과해야 한다."""
    blocked = harness.run_guard(harness_dir, case.command)
    assert blocked == case.expect_block, (
        f"{case.name!r}: 차단={blocked}, 기대={case.expect_block} (명령: {case.command})"
    )


# ------------------------------------------------------------ (2) 채점기 자기검증
@pytest.fixture(scope="module")
def selfcheck():
    """태스크당 golden/baseline × 조건 4회 채점. 무거우므로 모듈 스코프로 한 번만 돈다."""
    return {task.id: run.task_selfcheck(task) for task in TASKS}


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.id)
def test_golden_scores_full(selfcheck, task):
    """골든 산출물은 만점을 받아야 한다 — 정답을 오답으로 처리하지 않는다(false negative)."""
    scores, _ = selfcheck[task.id]
    assert all(v == 1.0 for v in scores["golden"].values()), f"golden={scores['golden']}"


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.id)
def test_baseline_stays_at_floor(selfcheck, task):
    """손대지 않은 시작 상태는 바닥에 머물러야 한다 — 미수행을 통과시키지 않는다(false positive)."""
    scores, _ = selfcheck[task.id]
    assert all(v <= run.BASELINE_CAP for v in scores["baseline"].values()), (
        f"baseline={scores['baseline']} (상한 {run.BASELINE_CAP})"
    )


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.id)
def test_no_condition_bias(selfcheck, task):
    """에이전트가 개입하지 않은 상태에서 두 조건 점수가 같아야 한다 — 채점기가 조건에 치우치지 않는다."""
    scores, _ = selfcheck[task.id]
    for mode in ("golden", "baseline"):
        assert len(set(scores[mode].values())) == 1, f"{mode} 조건 간 점수 불일치: {scores[mode]}"


# ------------------------------------------------- 하네스의 Stop 게이트(verify.sh) 정확도
def test_verify_gate_blocks_then_passes():
    """verify.sh 가 망가진 상태를 막고 골든 수정 후엔 통과해야 한다.

    태스크 01(실패하는 테스트)은 결함이 pytest 로 바로 드러나는 유일한 픽스처라 게이트
    정확도 검증에 쓴다. 다른 태스크의 결함(시크릿·경로 탈출 등)은 lint/test 로 잡히지 않으므로
    verify.sh 통과 여부로 채점하면 안 된다 — 그것이 held-out 채점기가 필요한 이유다.
    """
    task = next(t for t in TASKS if t.id.startswith("01"))
    with tempfile.TemporaryDirectory() as tmp:
        slot = Path(tmp) / "broken"
        slot.mkdir()
        repo = prepare(task, "harness", slot)
        assert not harness.run_verify(repo).passed, "망가진 상태인데 verify 가 통과함"
        apply_golden(task, repo)
        result = harness.run_verify(repo)
        assert result.passed, f"골든 수정 후에도 verify 실패:\n{result.output}"


# ------------------------------------------------------------- 스위트 구조 불변식
@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.id)
def test_heldout_assets_never_reach_workspace(task):
    """채점 자산(solution/)이 에이전트 작업공간에 새어 들어가지 않아야 한다.

    이 불변식이 깨지면 에이전트가 채점 테스트를 읽고 그것에 맞춰 통과시킬 수 있다 —
    벤치마크가 스스로를 속이는 가장 흔한 경로다.
    """
    with tempfile.TemporaryDirectory() as tmp:
        for condition in CONDITIONS:
            slot = Path(tmp) / condition
            slot.mkdir(parents=True)
            repo = prepare(task, condition, slot)
            leaked = [
                p.relative_to(repo).as_posix()
                for p in repo.rglob("*")
                if p.is_file() and ("heldout" in p.parts or p.name in ("grade.py", "finish.sh"))
            ]
            assert not leaked, f"[{task.id}/{condition}] 채점 자산 유출: {leaked}"


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.id)
def test_task_documents_its_criteria(task):
    """모든 태스크는 질의(README)와 채점 기준(solution/README)을 문서로 갖는다."""
    assert (task.dir / "README.md").exists(), "태스크 질의 문서 없음"
    rubric = task.dir / "solution" / "README.md"
    assert rubric.exists(), "채점 기준 문서 없음"
    text = rubric.read_text(encoding="utf-8")
    assert "가중" in text and "판정" in text, "채점 기준에 가중·판정 방법이 없음"
