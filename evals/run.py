"""경량 스코어카드 — LLM 없이 도는 결정론적 검증. CI 에서 항상 돈다.

    python -m evals.run

두 가지를 본다:

  (1) **guard-bash 차단 정확도** — 생성된 PreToolUse 가드가 위반 명령(`rm -rf`, force push,
      never_touch 스테이징, 파이프-투-셸, `--no-verify`)을 실제로 deny 하고 benign 은 통과시키는가.

  (2) **채점기 자기검증** — 각 태스크에 대해
        golden   : 골든 산출물을 덮으면 1.00 이 나오는가      (false negative 없음)
        baseline : 손대지 않은 시작 상태가 바닥에 머무는가     (false positive 없음)
        parity   : 두 모드 모두 조건 A·B 점수가 같은가         (조건 편향 없음)

(2)가 통과하지 않는 채점기의 A/B 결과는 읽을 가치가 없다. 그래서 실제 에이전트 실행
(`python -m evals.abrun --mode agent`)보다 이 검증을 CI 게이트로 둔다.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import harness  # noqa: E402
from abrun import CONDITIONS, apply_golden, grade, load_tasks, prepare  # noqa: E402

BASELINE_CAP = 0.15


def guard_scorecard() -> tuple[int, int, list[str]]:
    """타깃별로 가드 차단 정확도를 본다.

    도구마다 훅 페이로드와 deny 응답 스키마가 달라서, 한 타깃에서 통하는 가드가 다른 타깃에서는
    무력할 수 있다. 세 타깃을 각자의 형식으로 확인한다.
    """
    lines = ["== 경량 모드: guard-bash 차단 정확도 (타깃별) =="]
    passed = total = 0
    for target in sorted(harness.TARGETS):
        with tempfile.TemporaryDirectory() as tmp:
            harness_dir = Path(tmp)
            harness.materialize_harness(harness_dir, target=target)
            for path in harness_dir.glob(".scripts/*.sh"):
                path.chmod(0o755)
            hits = 0
            failed: list[str] = []
            for case in harness.GUARD_CASES:
                blocked = harness.run_guard(harness_dir, case.command, target)
                if blocked == case.expect_block:
                    hits += 1
                else:
                    failed.append(case.name)
            passed += hits
            total += len(harness.GUARD_CASES)
            mark = "✓" if not failed else "✗"
            suffix = f"  ← 실패: {', '.join(failed)}" if failed else ""
            lines.append(f"   {mark} {target:12} {hits}/{len(harness.GUARD_CASES)}{suffix}")
    return passed, total, lines


def task_selfcheck(task) -> tuple[dict[str, dict[str, float]], list[tuple[str, bool]]]:
    """한 태스크의 golden/baseline × 조건 점수와 판정 목록을 돌려준다."""
    scores: dict[str, dict[str, float]] = {"golden": {}, "baseline": {}}
    with tempfile.TemporaryDirectory() as tmp:
        for mode in ("golden", "baseline"):
            for condition in CONDITIONS:
                slot = Path(tmp) / mode / condition
                slot.mkdir(parents=True)
                repo = prepare(task, condition, slot)
                if mode == "golden":
                    apply_golden(task, repo)
                report = grade(task, repo, slot / "transcript.jsonl")
                scores[mode][condition] = report.get("score", 0.0)
                shutil.rmtree(repo, ignore_errors=True)
    checks = [
        ("golden=1.00", all(v == 1.0 for v in scores["golden"].values())),
        (f"baseline<={BASELINE_CAP}", all(v <= BASELINE_CAP for v in scores["baseline"].values())),
        (
            "조건 parity",
            len(set(scores["golden"].values())) == 1 and len(set(scores["baseline"].values())) == 1,
        ),
    ]
    return scores, checks


def grader_scorecard() -> tuple[int, int, list[str]]:
    lines = ["== 경량 모드: 채점기 자기검증 =="]
    passed = total = 0
    for task in load_tasks(None):
        scores, checks = task_selfcheck(task)
        passed += sum(1 for _, ok in checks if ok)
        total += len(checks)
        detail = " ".join(
            f"{mode}:{'/'.join(f'{v:.2f}' for v in scores[mode].values())}"
            for mode in ("golden", "baseline")
        )
        failed = [name for name, ok in checks if not ok]
        mark = "✓" if not failed else "✗"
        suffix = f"  ← 실패: {', '.join(failed)}" if failed else ""
        lines.append(f"   {mark} {task.id:26} {detail}{suffix}")
    return passed, total, lines


def main() -> int:
    g_pass, g_total, g_lines = guard_scorecard()
    s_pass, s_total, s_lines = grader_scorecard()
    print("\n".join(g_lines))
    print()
    print("\n".join(s_lines))
    print()
    print("== 스코어카드 ==")
    print(f"   guard-bash 차단 정확도: {g_pass}/{g_total} ({g_pass / g_total:.0%})")
    print(f"   채점기 자기검증: {s_pass}/{s_total} ({s_pass / s_total:.0%})")
    ok = g_pass == g_total and s_pass == s_total
    print("=" * 30)
    print(f"결과: {'PASS ✅' if ok else 'FAIL ❌'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
