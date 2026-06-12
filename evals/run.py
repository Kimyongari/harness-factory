"""eval 스코어카드 러너.

  python -m evals.run            # 경량 모드 (LLM 없음, CI 용)
  python -m evals.run --full     # 전체 모드 (실제 claude -p 구동; 비쌈)

경량 모드가 측정하는 것:
  (b) guard-bash 가 위반 명령을 차단하고 benign 은 통과시키는 차단 정확도
  (c) verify.sh Stop 게이트가 망가진 상태를 막고(골든 수정 후엔 통과시키는) 게이트 정확도

전체 모드가 추가로 측정하는 것:
  (a) 실제 에이전트가 골든 태스크를 풀어 verify.sh 를 통과시키는 골든패스 통과율
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from . import harness


def _eval_guard() -> tuple[int, int, list[str]]:
    """guard-bash 차단 정확도. (통과, 전체, 실패라인)."""
    lines: list[str] = []
    passed = 0
    with tempfile.TemporaryDirectory() as tmp:
        hdir = Path(tmp)
        harness.materialize_harness(hdir)
        for case in harness.GUARD_CASES:
            blocked = harness.run_guard(hdir, case.command)
            ok = blocked == case.expect_block
            passed += ok
            verb = "차단" if blocked else "허용"
            want = "차단" if case.expect_block else "허용"
            mark = "✓" if ok else "✗"
            lines.append(f"   {mark} [{verb:<2}/기대 {want:<2}] {case.name}")
            if not ok:
                lines.append(f"       명령: {case.command}")
    return passed, len(harness.GUARD_CASES), lines


def _eval_verify_gates() -> tuple[int, int, list[str]]:
    """각 골든 태스크: 망가진 상태 verify 실패 + 골든 수정 후 verify 통과. (통과, 전체, 라인)."""
    lines: list[str] = []
    passed = 0
    tasks = harness.load_tasks()
    total = len(tasks) * 2
    for task in tasks:
        with tempfile.TemporaryDirectory() as tmp:
            proj = harness.setup_task_workspace(task, Path(tmp))
            broken = harness.run_verify(proj)
            ok_broken = not broken.passed
            passed += ok_broken
            lines.append(
                f"   {'✓' if ok_broken else '✗'} [{task.id}] 망가진 상태 → verify "
                f"{'막힘(기대)' if ok_broken else f'통과해버림(exit {broken.exit_code})'}"
            )
            harness.apply_solution(task, proj)
            fixed = harness.run_verify(proj)
            passed += fixed.passed
            lines.append(
                f"   {'✓' if fixed.passed else '✗'} [{task.id}] 골든 수정 후 → verify "
                f"{'통과(기대)' if fixed.passed else f'실패(exit {fixed.exit_code})'}"
            )
            if not fixed.passed:
                lines.append("       --- verify 출력 ---")
                lines += [f"       {ln}" for ln in fixed.output.strip().splitlines()]
    return passed, total, lines


def _eval_golden_path() -> tuple[int, int, list[str]]:
    """전체 모드: 실제 에이전트가 태스크를 풀어 verify 통과시키는 비율. (통과, 전체, 라인)."""
    lines: list[str] = []
    passed = 0
    tasks = harness.load_tasks()
    for task in tasks:
        with tempfile.TemporaryDirectory() as tmp:
            proj = harness.setup_task_workspace(task, Path(tmp))
            try:
                harness.run_agent(task.prompt, proj)
            except Exception as e:  # noqa: BLE001 — 에이전트 구동 실패는 그 태스크 실패로 기록
                lines.append(f"   ✗ [{task.id}] 에이전트 구동 오류: {e}")
                continue
            result = harness.run_verify(proj)
            passed += result.passed
            lines.append(
                f"   {'✓' if result.passed else '✗'} [{task.id}] {task.title} → verify "
                f"{'통과' if result.passed else f'실패(exit {result.exit_code})'}"
            )
    return passed, len(tasks), lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="생성 하네스 eval 스코어카드")
    parser.add_argument(
        "--full", action="store_true", help="실제 에이전트로 골든패스 통과율까지 측정"
    )
    args = parser.parse_args(argv)

    sections: list[tuple[str, int, int, list[str]]] = []

    print("== 경량 모드: guard-bash 차단 정확도 ==")
    gp, gt, gl = _eval_guard()
    print("\n".join(gl))
    sections.append(("guard-bash 차단 정확도", gp, gt, gl))

    print("\n== 경량 모드: verify.sh Stop 게이트 ==")
    vp, vt, vl = _eval_verify_gates()
    print("\n".join(vl))
    sections.append(("verify Stop 게이트", vp, vt, vl))

    if args.full:
        active, reason = harness.full_mode_status()
        print(f"\n== 전체 모드: 골든패스 통과율 == ({reason})")
        if active:
            ap, at, al = _eval_golden_path()
            print("\n".join(al))
            sections.append(("골든패스 통과율", ap, at, al))
        else:
            print("   (건너뜀)")

    print("\n== 스코어카드 ==")
    all_pass = True
    for name, p, t, _ in sections:
        pct = (100 * p // t) if t else 0
        print(f"   {name}: {p}/{t} ({pct}%)")
        all_pass = all_pass and (p == t)
    print("=" * 30)
    print("결과:", "PASS ✅" if all_pass else "FAIL ❌")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
