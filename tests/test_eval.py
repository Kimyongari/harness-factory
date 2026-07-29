"""eval 스위트 자체를 검증하는 테스트 — LLM 없이 돌기 때문에 CI 에서 항상 돈다.

`test_engine.py` 가 생성기 산출물의 *모양*을 보는 단위테스트라면, 여기서는

  (1) 생성된 PreToolUse 가드가 위반 명령을 실제로 **차단**하는가 (행동)
  (2) A/B 채점기가 **정답을 인정하고 미수행을 걸러내며 조건 편향이 없는가** (채점기의 채점)

를 본다. (2)가 깨진 상태의 A/B 결과는 신뢰할 수 없으므로, 실제 에이전트 실행을 CI 에 넣는 대신
이 자기검증을 게이트로 둔다. 실제 A/B 실행은 `python -m evals.abrun --mode agent`.
"""

import json
import tempfile
from pathlib import Path

import pytest

from evals import harness, run
from evals.abrun import (
    CONDITIONS,
    MECHANISMS,
    RUNNERS,
    apply_golden,
    load_tasks,
    prepare,
)
from evals.grading import bash_commands, final_message

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


# --------------------------------------------------------- 다중 타깃 (codex / cursor)
@pytest.mark.parametrize("target", sorted(harness.TARGETS))
def test_harness_materializes_for_every_target(target):
    """세 타깃 모두 하네스가 깔리고, 각자의 지시문 파일과 공용 `.scripts/` 를 갖는다."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        harness.materialize_harness(d, target=target)
        rels = {p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file()}
        expected_instructions = {
            "claude-code": "CLAUDE.md",
            "codex": "AGENTS.md",
            "cursor": ".cursor/rules/00-overview.mdc",
        }[target]
        assert expected_instructions in rels, f"{target} 지시문 파일 없음: {sorted(rels)[:8]}"
        # 강제 장치는 세 타깃이 공유한다 — 그래야 A/B 결과를 타깃 간에 비교할 수 있다.
        assert ".scripts/guard-bash.sh" in rels
        assert ".scripts/verify.sh" in rels


@pytest.mark.parametrize("target", sorted(harness.TARGETS))
@pytest.mark.parametrize("case", harness.GUARD_CASES, ids=lambda c: c.name)
def test_guard_blocks_violations_for_every_target(target, case):
    """가드가 **각 도구의 훅 페이로드·deny 스키마**로 동작하는가.

    도구마다 명령을 담는 자리(`tool_input.command` vs top-level `command`)와 deny 응답
    형식(`permissionDecision` vs `permission`)이 다르다. 형식이 틀리면 가드가 차단 문구를
    출력해도 런타임은 그것을 차단으로 해석하지 못한다 — 있으나 마나가 된다.
    """
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        harness.materialize_harness(d, target=target)
        for path in d.glob(".scripts/*.sh"):
            path.chmod(0o755)
        blocked = harness.run_guard(d, case.command, target)
        assert blocked == case.expect_block, (
            f"[{target}] {case.name!r}: 차단={blocked}, 기대={case.expect_block}"
        )


def test_every_target_has_a_declared_runner():
    """평가 대상 타깃에는 모두 실행 방법이 선언돼 있어야 한다."""
    assert set(RUNNERS) == set(harness.TARGETS)
    for target, runner in RUNNERS.items():
        assert runner.binary, target
        assert runner.note, f"{target}: 러너 주의사항이 비어 있다"
        argv = runner.build("do the thing", "some-model", Path("/tmp/s.json"))
        assert argv[0] == runner.binary
        assert "do the thing" in argv, f"{target}: 프롬프트가 명령에 없다"
        assert "some-model" in argv, f"{target}: 모델이 명령에 없다"


def test_runner_verification_status_is_honest():
    """실측한 러너와 문서만 보고 적은 러너를 구분해 표시해야 한다.

    미검증 러너를 검증된 것처럼 두면, 실패했을 때 원인이 하네스인지 CLI 인자인지 구분되지 않는다.
    """
    assert RUNNERS["claude-code"].verified is True
    for target in ("codex", "cursor"):
        assert RUNNERS[target].verified is False, (
            f"{target} 러너를 실제로 돌려 검증했다면 verified=True 로 바꾸고 이 테스트를 갱신하라"
        )


# ------------------------------------------------- 트랜스크립트 추출 (도구 무관)
# 도구별 트랜스크립트 스키마 샘플. 파서가 한 형식에만 맞으면 다른 도구에서 조용히 빈 목록이
# 나오고, 그러면 프로세스 축(우회 탐지)이 아무것도 못 잡은 채 통과한다.
TRANSCRIPT_SAMPLES = {
    "claude-code-stream-json": [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "git commit --no-verify -m x"},
                    }
                ]
            },
        },
        {"type": "result", "subtype": "success", "result": "완료했습니다. 우회는 없었습니다."},
    ],
    "codex-json": [
        {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "command": "git commit --no-verify -m x",
                "exit_code": 0,
            },
        },
        {
            "type": "item.completed",
            "item": {"type": "assistant_message", "text": "완료했습니다. 우회는 없었습니다."},
        },
    ],
    "cursor-stream-json": [
        {"type": "tool_call", "tool": "terminal", "command": "git commit --no-verify -m x"},
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "완료했습니다. 우회는 없었습니다."}]},
        },
    ],
}


@pytest.mark.parametrize("fmt", sorted(TRANSCRIPT_SAMPLES))
def test_bash_commands_extracted_from_every_transcript_format(monkeypatch, tmp_path, fmt):
    """세 도구의 트랜스크립트에서 실행된 셸 명령을 모두 뽑아내는가."""
    path = tmp_path / "transcript.jsonl"
    path.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in TRANSCRIPT_SAMPLES[fmt]),
        encoding="utf-8",
    )
    monkeypatch.setenv("EVAL_TRANSCRIPT", str(path))
    cmds = bash_commands(tmp_path)
    assert any("--no-verify" in c for c in cmds), f"[{fmt}] 셸 명령을 놓쳤다: {cmds}"


@pytest.mark.parametrize("fmt", sorted(TRANSCRIPT_SAMPLES))
def test_final_message_extracted_from_every_transcript_format(monkeypatch, tmp_path, fmt):
    """세 도구의 트랜스크립트에서 최종 보고문을 뽑아내는가(정직성 축 채점 입력)."""
    path = tmp_path / "transcript.jsonl"
    path.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in TRANSCRIPT_SAMPLES[fmt]),
        encoding="utf-8",
    )
    monkeypatch.setenv("EVAL_TRANSCRIPT", str(path))
    assert "완료했습니다" in final_message(tmp_path), f"[{fmt}] 최종 보고문을 못 찾았다"


def test_unrelated_command_fields_are_not_treated_as_shell_calls():
    """`command` 라는 이름의 무관한 필드를 실행된 명령으로 오인하지 않는가.

    오탐이 생기면 04·05·11·12·18 태스크가 하지 않은 우회를 했다고 판정한다.
    """
    import os

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        path = ws / "transcript.jsonl"
        path.write_text(
            json.dumps(
                {
                    "type": "tool_use",
                    "name": "Write",
                    "input": {
                        "file_path": "hooks.json",
                        "content": '{"command": "git push --force"}',
                    },
                }
            )
            + "\n"
            + json.dumps({"type": "config", "name": "Edit", "command": "git push --force"})
            + "\n",
            encoding="utf-8",
        )
        os.environ["EVAL_TRANSCRIPT"] = str(path)
        try:
            assert bash_commands(ws) == [], "셸 호출이 아닌 command 필드를 잡았다"
        finally:
            os.environ.pop("EVAL_TRANSCRIPT", None)


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
def test_task_declares_how_the_harness_could_help(task):
    """모든 태스크는 '하네스가 어떤 장치로 차이를 만들 것인지' 를 선언해야 한다.

    선언이 없으면 무승부가 나왔을 때 두 가지를 구분할 수 없다:
      (a) 하네스에 그 장치가 없어서 애초에 차이가 날 수 없었다
      (b) 장치는 있었는데 효과가 없었다
    (a) 를 (b) 로 오독하면 "하네스 무효" 라는 잘못된 결론이 나온다.
    """
    assert task.mechanism in MECHANISMS, f"{task.id}: 알 수 없는 기제 {task.mechanism!r}"


def test_deterministic_mechanisms_actually_exist_in_the_harness():
    """`guard-bash`·`verify-gate`·`git-hook`·`scaffold` 를 선언한 태스크는
    그 장치가 생성 하네스에 실제로 있어야 한다. 없으면 그 태스크는 사실상 skill-text 다."""
    artifacts = {
        "guard-bash": ".scripts/guard-bash.sh",
        "verify-gate": ".scripts/verify.sh",
        "git-hook": ".githooks/pre-push",
        "scaffold": ".gitignore",
    }
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        harness.materialize_harness(d)
        present = {p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file()}
    for task in TASKS:
        artifact = artifacts.get(task.mechanism)
        if artifact is None:
            continue
        assert artifact in present, (
            f"{task.id} 는 {task.mechanism} 을 전제하는데 하네스에 {artifact} 가 없다"
        )


def test_control_task_declares_no_mechanism():
    """대조군은 기제가 없어야 한다 — 하네스가 이기면 벤치마크가 기울었다는 신호다."""
    control = [t for t in TASKS if t.control]
    assert control, "대조군 태스크가 없다 — 벤치마크 자기 진단 장치가 사라졌다"
    for task in control:
        assert task.mechanism == "none", f"{task.id}: 대조군인데 기제={task.mechanism}"


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.id)
def test_task_documents_its_criteria(task):
    """모든 태스크는 질의(README)와 채점 기준(solution/README)을 문서로 갖는다."""
    assert (task.dir / "README.md").exists(), "태스크 질의 문서 없음"
    rubric = task.dir / "solution" / "README.md"
    assert rubric.exists(), "채점 기준 문서 없음"
    text = rubric.read_text(encoding="utf-8")
    assert "가중" in text and "판정" in text, "채점 기준에 가중·판정 방법이 없음"
