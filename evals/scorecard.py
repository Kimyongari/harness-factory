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
            "agent 모드 결과가 없다. python -m evals.abrun --mode agent 를 먼저 돌릴 것."
        )
    return dirs[-1]


def _mean(values: list[float]) -> float:
    return round(statistics.mean(values), 3) if values else 0.0


def _completion(rows: list[dict]) -> float | None:
    """완료 평균. 옛 실행은 이 필드가 없다(그때는 점수만 기록했다) → None."""
    vals = [r["completion"] for r in rows if r.get("completion") is not None]
    return _mean(vals) if vals else None


def _fmt(value, unit: str = "") -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:,.2f}{unit}"
    return f"{value:,}{unit}"


def build(out_dir: Path) -> str:
    data = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    runs = data["runs"]
    tasks: list[str] = sorted({r["task"] for r in runs})
    axis = {r["task"]: None for r in runs}
    mechanism: dict[str, str] = {}
    category: dict[str, str] = {}
    difficulty: dict[str, str] = {}

    import yaml

    for tid in tasks:
        meta = yaml.safe_load((EVALS / "tasks" / tid / "task.yaml").read_text(encoding="utf-8"))
        axis[tid] = f"{meta.get('axis', '?')}{' · 대조군' if meta.get('control') else ''}"
        mechanism[tid] = meta.get("mechanism", "skill-text")
        category[tid] = meta.get("category", "trap")
        difficulty[tid] = meta.get("difficulty", "medium")

    # 무효 슬롯(에이전트 미실행 등 인프라 사고)은 측정값이 아니므로 평균에서 뺀다.
    # 빼지 않으면 무효가 몰린 쪽이 부당하게 낮아져 결론이 뒤집힌다(FINDINGS 의 v2·v3 사례).
    invalid = [r for r in runs if r.get("invalid")]

    def by(tid: str, cond: str) -> list[dict]:
        return [
            r for r in runs if r["task"] == tid and r["condition"] == cond and not r.get("invalid")
        ]

    L: list[str] = []
    L.append(f"# 스코어카드: {data['stamp']}")
    L.append("")
    L.append(
        f"모델 `{data['model']}` · 모드 `{data['mode']}` · 반복 {data['repeats']}회 · "
        f"태스크 {len(tasks)}종 × 조건 2 = 실행 {len(runs)}건"
    )
    meta = data.get("meta") or {}
    if meta.get("harness_commit"):
        dirty = " (uncommitted 변경 있음)" if meta.get("harness_dirty") else ""
        L.append("")
        L.append(
            f"하네스 커밋 `{meta['harness_commit'][:9]}`{dirty} · {meta.get('cli_version', '')}"
        )
    L.append("")
    if invalid:
        L.append(
            f"> ⚠️ **무효 {len(invalid)}건**: 에이전트가 실제로 실행되지 않은 슬롯이다. "
            "아래 모든 평균에서 제외했다. 무효가 한 조건에 몰리면 Δ 가 왜곡되므로 "
            "재실행으로 교체하는 것을 권한다."
        )
        for r in invalid:
            L.append(f">   - `{r['task']}` · {r['condition']}: {r['invalid']}")
        L.append("")
    L.append("> 채점 방법·공정성 장치·한계는 [`../README.md`](../README.md) 참고.")
    L.append("")

    # ------------------------------------------------------------------ 효과
    L.append("## 효과: 점수")
    L.append("")
    # 완료(Completion)를 점수와 나란히 낸다. `score = completion × process` 라서 둘을
    # 합쳐놓으면 "요구를 못 채운 것" 과 "예산을 넘긴 것" 이 같은 숫자로 보인다.
    L.append("| 태스크 | 축 | A. harness | B. bare | Δ (A−B) | 완료 A/B | fatal |")
    L.append("|---|---|---|---|---|---|---|")
    a_all, b_all = [], []
    ca_all, cb_all = [], []
    fatal_rows = []
    for tid in tasks:
        ra, rb = by(tid, "harness"), by(tid, "bare")
        af = sum(1 for r in ra if r["fatal"])
        bf = sum(1 for r in rb if r["fatal"])
        if af or bf:
            fatal_rows.append((tid, af, bf))
        fatal_cell = f"A:{af} / B:{bf}" if (af or bf) else "-"

        # 한쪽이라도 유효 실행이 0건이면 비교 자체가 불가능하다. 0.00 으로 세면
        # 무효가 몰린 조건이 부당하게 깎여, 무효를 배제한 이유가 무색해진다.
        if not ra or not rb:
            L.append(f"| {tid} | {axis[tid]} | - | - | 측정 불가 | - | {fatal_cell} |")
            continue

        a, b = _mean([r["score"] for r in ra]), _mean([r["score"] for r in rb])
        a_all.append(a)
        b_all.append(b)
        ca, cb = _completion(ra), _completion(rb)
        comp_cell = "-" if ca is None or cb is None else f"{ca:.2f} / {cb:.2f}"
        if ca is not None and cb is not None:
            ca_all.append(ca)
            cb_all.append(cb)
        delta = a - b
        mark = "🟢" if delta > 0.05 else ("🔴" if delta < -0.05 else "⚪")
        L.append(
            f"| {tid} | {axis[tid]} | {a:.2f} | {b:.2f} | {mark} {delta:+.2f} "
            f"| {comp_cell} | {fatal_cell} |"
        )
    if a_all:
        comp_avg = f"**{_mean(ca_all):.2f} / {_mean(cb_all):.2f}**" if ca_all and cb_all else "-"
        L.append(
            f"| **평균** | | **{_mean(a_all):.2f}** | **{_mean(b_all):.2f}** | "
            f"**{_mean(a_all) - _mean(b_all):+.2f}** | {comp_avg} | |"
        )
        L.append("")
        L.append(f"평균은 비교 가능한 **{len(a_all)}개 태스크**만으로 계산했다.")
        if ca_all and cb_all and abs(_mean(ca_all) - _mean(cb_all)) < 0.005:
            L.append("")
            L.append(
                "> **완료(Completion)는 동률이다.** 점수 차이는 전부 Process 축"
                "(예산 대비 토큰 효율·차단 후 복구·검사 우회)에서 나왔다 — 요구를 못 채운 게 "
                "아니라 더 비싸게 채운 것이다. 비용 표를 함께 읽어야 한다."
            )
    else:
        L.append("| **평균** | | - | - | 비교 가능한 태스크 없음 | - | |")
    L.append("")
    total_af = sum(1 for r in runs if r["condition"] == "harness" and r["fatal"])
    total_bf = sum(1 for r in runs if r["condition"] == "bare" and r["fatal"])
    L.append(
        f"**fatal 발생**: harness **{total_af}건** / bare **{total_bf}건** "
        f"(평균에 섞지 않고 건수로 본다. 보안 사고는 상계되지 않는다)"
    )
    L.append("")

    # ------------------------------------------------------------------ 비용
    L.append("## 비용: 토큰·시간")
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
            k: sum(float(r[k] or 0) for r in runs if r["condition"] == c and not r.get("invalid"))
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
                f"출력 토큰 {extra:,.0f}개를 더 써서 평균 점수 **{gain:+.2f}** 를 얻었다 "
                f"(1k 토큰당 {gain / (extra / 1000):+.4f}점)."
            )
    L.append("")

    # -------------------------------------------------- 카테고리·난이도별 집계
    # "어디서(어떤 워크플로에서), 얼마나 어려울 때 갈리는가" 를 표 하나로 읽게 한다.
    # 스위트 v2 가 포화된 뒤 난이도 계층화(Don't Blame 방식)를 도입한 이유가 이 표다.
    def _group_table(name: str, key: dict[str, str]) -> None:
        L.append(f"## {name}별 점수")
        L.append("")
        L.append(f"| {name} | 태스크 수 | A 평균 | B 평균 | Δ |")
        L.append("|---|---|---|---|---|")
        groups: dict[str, list[str]] = {}
        for tid in tasks:
            groups.setdefault(key.get(tid, "?"), []).append(tid)
        for group in sorted(groups):
            tids = [t for t in groups[group] if by(t, "harness") and by(t, "bare")]
            if not tids:
                L.append(f"| {group} | {len(groups[group])} | - | - | 측정 불가 |")
                continue
            a = _mean([_mean([r["score"] for r in by(t, "harness")]) for t in tids])
            b = _mean([_mean([r["score"] for r in by(t, "bare")]) for t in tids])
            mark = "🟢" if a - b > 0.05 else ("🔴" if a - b < -0.05 else "⚪")
            L.append(f"| {group} | {len(tids)} | {a:.2f} | {b:.2f} | {mark} {a - b:+.2f} |")
        L.append("")

    _group_table("카테고리", category)
    _group_table("난이도", difficulty)

    # ------------------------------------------------------------ 기제별 집계
    # skill-text 태스크의 무승부를 "하네스 무효" 로 오독하지 않기 위한 절.
    # 결정론적 기제가 없는 태스크에서 차이가 안 나는 것은 예상된 결과다.
    L.append("## 어떤 기제가 차이를 만들었나")
    L.append("")
    L.append(
        "각 태스크는 `task.yaml` 에 하네스가 어떤 장치로 차이를 만들 것인지 선언한다. "
        "`skill-text` 는 결정론적 검사 없이 지시문 문장에만 의존하는 태스크로, "
        "프론티어 모델에서는 무승부가 예상된다."
    )
    L.append("")
    L.append("| 기제 | 태스크 수 | A 평균 | B 평균 | Δ |")
    L.append("|---|---|---|---|---|")
    by_mech: dict[str, list[str]] = {}
    for tid in tasks:
        by_mech.setdefault(mechanism.get(tid, "skill-text"), []).append(tid)
    for mech in sorted(by_mech, key=lambda m: (m == "skill-text", m)):
        # 한쪽이라도 유효 실행이 없는 태스크는 뺀다(점수 표와 같은 이유).
        tids = [t for t in by_mech[mech] if by(t, "harness") and by(t, "bare")]
        if not tids:
            L.append(f"| `{mech}` | {len(by_mech[mech])} | - | - | 측정 불가 |")
            continue
        a = _mean([_mean([r["score"] for r in by(t, "harness")]) for t in tids])
        b = _mean([_mean([r["score"] for r in by(t, "bare")]) for t in tids])
        mark = "🟢" if a - b > 0.05 else ("🔴" if a - b < -0.05 else "⚪")
        L.append(f"| `{mech}` | {len(tids)} | {a:.2f} | {b:.2f} | {mark} {a - b:+.2f} |")
    L.append("")
    deterministic = [t for m, ts in by_mech.items() if m not in ("skill-text", "none") for t in ts]
    L.append(
        f"결정론적 기제가 있는 태스크 **{len(deterministic)}개**, "
        f"지시문에만 의존하는 태스크 **{len(by_mech.get('skill-text', []))}개**."
    )
    L.append("")

    # -------------------------------------------------------- 항목 단위 차이
    L.append("## 어디서 갈렸나: 항목 단위 차이")
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
        L.append("| - | 조건 간 판정이 갈린 항목이 없다 | | | |")
    L.append("")

    # ------------------------------------------------------------ 실행 오류
    errors = [r for r in runs if r.get("agent_error")]
    if errors:
        L.append("## 실행 경고")
        L.append("")
        for r in errors:
            L.append(f"- `{r['task']}` / {r['condition']}: {r['agent_error'][:200]}")
        L.append("")

    L.append("---")
    L.append("")
    L.append(
        # 같은 디렉터리 안의 파일을 상대 링크로 건다. 디렉터리 이름을 박으면
        # 결과 폴더를 규약대로 옮길 때마다 링크가 깨진다(실제로 전부 깨졌다).
        f"원시 데이터: [`summary.json`](summary.json) · 실행별 트랜스크립트는 `{data['workroot']}`"
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
