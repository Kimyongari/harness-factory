"""summary.json → 사람이 읽는 스코어카드(Markdown).

    python -m evals.scorecard                       # 최신 agent 실행
    python -m evals.scorecard evals/results/<dir>   # 특정 실행

효과(점수·fatal)와 비용(토큰·시간)을 **나란히** 낸다. 하네스는 거의 항상 비용을 올리므로
효과만 보면 판단이 안 된다. 항목 단위 차이표까지 내서 "어디서 갈렸는지"를 보이게 한다.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

EVALS = Path(__file__).resolve().parent
RESULTS = EVALS / "results"
CONDS = ("harness", "bare")


def latest_dir() -> Path:
    dirs = sorted(d for d in RESULTS.glob("*-agent") if (d / "summary.json").exists())
    if not dirs:
        raise SystemExit(
            "agent 모드 결과가 없다. python -m evals.abrun --mode agent 를 먼저 돌려라."
        )
    return dirs[-1]


def _mean(values: list[float]) -> float:
    return round(statistics.mean(values), 3) if values else 0.0


def _fmt(value, unit: str = "") -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:,.2f}{unit}"
    return f"{value:,}{unit}"


def build(out_dir: Path) -> str:
    data = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    runs = data["runs"]
    tasks: list[str] = sorted({r["task"] for r in runs})
    axis = {r["task"]: None for r in runs}

    import yaml

    for tid in tasks:
        meta = yaml.safe_load((EVALS / "tasks" / tid / "task.yaml").read_text(encoding="utf-8"))
        axis[tid] = f"{meta.get('axis', '?')}{' · 대조군' if meta.get('control') else ''}"

    def by(tid: str, cond: str) -> list[dict]:
        return [r for r in runs if r["task"] == tid and r["condition"] == cond]

    L: list[str] = []
    L.append(f"# 스코어카드 — {data['stamp']}")
    L.append("")
    L.append(
        f"모델 `{data['model']}` · 모드 `{data['mode']}` · 반복 {data['repeats']}회 · "
        f"태스크 {len(tasks)}종 × 조건 2 = 실행 {len(runs)}건"
    )
    L.append("")
    L.append("> 채점 방법·공정성 장치·한계는 [`../README.md`](../README.md) 참고.")
    L.append("")

    # ------------------------------------------------------------------ 효과
    L.append("## 효과 — 점수")
    L.append("")
    L.append("| 태스크 | 축 | A. harness | B. bare | Δ (A−B) | fatal |")
    L.append("|---|---|---|---|---|---|")
    a_all, b_all = [], []
    fatal_rows = []
    for tid in tasks:
        a = _mean([r["score"] for r in by(tid, "harness")])
        b = _mean([r["score"] for r in by(tid, "bare")])
        a_all.append(a)
        b_all.append(b)
        af = sum(1 for r in by(tid, "harness") if r["fatal"])
        bf = sum(1 for r in by(tid, "bare") if r["fatal"])
        if af or bf:
            fatal_rows.append((tid, af, bf))
        delta = a - b
        mark = "🟢" if delta > 0.05 else ("🔴" if delta < -0.05 else "⚪")
        fatal_cell = f"A:{af} / B:{bf}" if (af or bf) else "—"
        L.append(
            f"| {tid} | {axis[tid]} | {a:.2f} | {b:.2f} | {mark} {delta:+.2f} | {fatal_cell} |"
        )
    L.append(
        f"| **평균** | | **{_mean(a_all):.2f}** | **{_mean(b_all):.2f}** | "
        f"**{_mean(a_all) - _mean(b_all):+.2f}** | |"
    )
    L.append("")
    total_af = sum(1 for r in runs if r["condition"] == "harness" and r["fatal"])
    total_bf = sum(1 for r in runs if r["condition"] == "bare" and r["fatal"])
    L.append(
        f"**fatal 발생**: harness **{total_af}건** / bare **{total_bf}건** "
        f"(평균에 섞지 않고 건수로 본다 — 보안 사고는 상계되지 않는다)"
    )
    L.append("")

    # ------------------------------------------------------------------ 비용
    L.append("## 비용 — 토큰·시간")
    L.append("")
    L.append(
        "| 태스크 | A 토큰(out) | B 토큰(out) | A 시간 | B 시간 | A 턴 | B 턴 | A 비용 | B 비용 |"
    )
    L.append("|---|---|---|---|---|---|---|---|---|")

    def agg(rows: list[dict], key: str):
        vals = [r[key] for r in rows if r.get(key) is not None]
        return _mean([float(v) for v in vals]) if vals else None

    for tid in tasks:
        ra, rb = by(tid, "harness"), by(tid, "bare")
        L.append(
            f"| {tid} | {_fmt(agg(ra, 'tokens_out'))} | {_fmt(agg(rb, 'tokens_out'))} "
            f"| {_fmt(agg(ra, 'duration_s'), 's')} | {_fmt(agg(rb, 'duration_s'), 's')} "
            f"| {_fmt(agg(ra, 'num_turns'))} | {_fmt(agg(rb, 'num_turns'))} "
            f"| ${_fmt(agg(ra, 'cost_usd'))} | ${_fmt(agg(rb, 'cost_usd'))} |"
        )
    tot = {
        c: {
            k: sum(float(r[k] or 0) for r in runs if r["condition"] == c)
            for k in ("tokens_out", "duration_s", "cost_usd")
        }
        for c in CONDS
    }
    L.append(
        f"| **합계** | {tot['harness']['tokens_out']:,.0f} | {tot['bare']['tokens_out']:,.0f} "
        f"| {tot['harness']['duration_s']:,.0f}s | {tot['bare']['duration_s']:,.0f}s | | "
        f"| ${tot['harness']['cost_usd']:,.2f} | ${tot['bare']['cost_usd']:,.2f} |"
    )
    L.append("")
    if tot["bare"]["cost_usd"]:
        ratio = tot["harness"]["cost_usd"] / tot["bare"]["cost_usd"]
        L.append(f"하네스 조건의 비용은 바닐라의 **{ratio:.2f}배**.")
        gain = _mean(a_all) - _mean(b_all)
        extra = tot["harness"]["tokens_out"] - tot["bare"]["tokens_out"]
        if extra > 0:
            L.append("")
            L.append(
                f"출력 토큰 {extra:,.0f} 개를 더 써서 평균 점수 **{gain:+.2f}** 를 얻었다 "
                f"(1k 토큰당 {gain / (extra / 1000):+.4f}점)."
            )
    L.append("")

    # -------------------------------------------------------- 항목 단위 차이
    L.append("## 어디서 갈렸나 — 항목 단위 차이")
    L.append("")
    L.append("점수가 같아도 통과한 항목이 다를 수 있다. 조건 간 판정이 갈린 항목만 추린다.")
    L.append("")
    L.append("| 태스크 | 항목 | harness | bare | 성격 |")
    L.append("|---|---|---|---|---|")
    any_diff = False
    for tid in tasks:
        ca = {c["id"]: c for r in by(tid, "harness") for c in r["criteria"]}
        cb = {c["id"]: c for r in by(tid, "bare") for c in r["criteria"]}
        for cid in ca.keys() | cb.keys():
            pa, pb = ca.get(cid, {}).get("pass"), cb.get(cid, {}).get("pass")
            if pa == pb:
                continue
            any_diff = True
            meta = ca.get(cid) or cb.get(cid) or {}
            kind = "fatal" if meta.get("fatal") else ("gate" if meta.get("gate") else "")
            label = meta.get("label", cid)
            L.append(
                f"| {tid} | `{cid}` {label} | {'✅' if pa else '❌'} | {'✅' if pb else '❌'} | {kind} |"
            )
    if not any_diff:
        L.append("| — | 조건 간 판정이 갈린 항목이 없다 | | | |")
    L.append("")

    # ------------------------------------------------------------ 실행 오류
    errors = [r for r in runs if r.get("agent_error")]
    if errors:
        L.append("## 실행 경고")
        L.append("")
        for r in errors:
            L.append(f"- `{r['task']}` / {r['condition']} — {r['agent_error'][:200]}")
        L.append("")

    L.append("---")
    L.append("")
    L.append(
        f"원시 데이터: [`{out_dir.name}/summary.json`]({out_dir.name}/summary.json) · "
        f"실행별 트랜스크립트는 `{data['workroot']}`"
    )
    return "\n".join(L) + "\n"


def main() -> int:
    out_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else latest_dir()
    text = build(out_dir)
    (out_dir / "scorecard.md").write_text(text, encoding="utf-8")
    (RESULTS / "LATEST.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
