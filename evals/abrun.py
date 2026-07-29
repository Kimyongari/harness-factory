"""A/B 러너 — 같은 태스크를 '하네스 있음/없음' 두 조건에서 돌리고 held-out 채점한다.

    python -m evals.abrun --mode golden                  # 채점기 자기검증 (LLM 없음)
    python -m evals.abrun --mode baseline                # 시작 상태 채점 (LLM 없음)
    python -m evals.abrun --mode agent --tasks 02,05      # 실제 에이전트 A/B

설계 규칙 (자세한 근거는 evals/README.md):
  1. 두 조건은 **하네스 존재 여부만** 다르다. 모델·프롬프트·권한 설정·타임아웃·시작 상태는 동일하다.
  2. 채점 자산(held-out 테스트)은 작업공간 밖에 있고, 채점 시점에만 임시로 들어갔다 지워진다.
  3. 작업공간은 레포 밖(스크래치)에 만든다. 에이전트가 파괴적 명령을 실행해도 레포·홈이 다치지 않는다.
  4. 모든 실행은 트랜스크립트(stream-json)를 남긴다 — 프로세스·정직성 축은 파일 상태로는 볼 수 없다.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness import materialize_harness  # noqa: E402

EVALS = Path(__file__).resolve().parent
REPO = EVALS.parent
TASKS_DIR = EVALS / "tasks"
RESULTS_DIR = EVALS / "results"

CONDITIONS = ("harness", "bare")

# 두 조건에 **동일하게** 주는 권한 설정. 하네스의 이점이 "권한을 더 받았기 때문"이 되지 않도록
# 공통 분모를 명시적으로 고정한다. 네트워크 도구는 양쪽 다 막아 실행 간 변동을 줄인다.
FAIR_SETTINGS = {
    "permissions": {
        "allow": [
            "Read",
            "Edit",
            "Write",
            "Glob",
            "Grep",
            "TodoWrite",
            "Task",
            "Skill",
            "NotebookEdit",
            "Bash(git:*)",
            "Bash(python:*)",
            "Bash(python3:*)",
            "Bash(pytest:*)",
            "Bash(ruff:*)",
            "Bash(uv:*)",
            "Bash(pip:*)",
            "Bash(ls:*)",
            "Bash(cat:*)",
            "Bash(head:*)",
            "Bash(tail:*)",
            "Bash(grep:*)",
            "Bash(rg:*)",
            "Bash(find:*)",
            "Bash(wc:*)",
            "Bash(sed:*)",
            "Bash(awk:*)",
            "Bash(echo:*)",
            "Bash(printf:*)",
            "Bash(touch:*)",
            "Bash(mkdir:*)",
            "Bash(cp:*)",
            "Bash(mv:*)",
            "Bash(rm:*)",
            "Bash(chmod:*)",
            "Bash(bash:*)",
            "Bash(sh:*)",
            "Bash(env:*)",
            "Bash(pwd)",
            "Bash(which:*)",
            "Bash(true)",
            "Bash(diff:*)",
            "Bash(tree:*)",
            "Bash(du:*)",
        ],
        "deny": ["WebSearch", "WebFetch"],
    }
}


@dataclass
class RunResult:
    task: str
    condition: str
    repeat: int
    mode: str
    score: float
    fatal: bool
    criteria: list
    duration_s: float
    num_turns: int | None = None
    cost_usd: float | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    agent_error: str | None = None
    workspace: str = ""


# --------------------------------------------------------------------------- tasks
@dataclass
class Task:
    id: str
    title: str
    axis: str
    prompt: str
    timeout_s: int
    control: bool
    dir: Path


def load_tasks(selector: str | None) -> list[Task]:
    import yaml

    wanted = [s.strip() for s in selector.split(",")] if selector else None
    tasks = []
    for meta_path in sorted(TASKS_DIR.glob("*/task.yaml")):
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
        tid = meta["id"]
        if wanted and not any(w == tid or tid.startswith(w) for w in wanted):
            continue
        tasks.append(
            Task(
                id=tid,
                title=meta.get("title", tid),
                axis=meta.get("axis", "?"),
                prompt=meta["prompt"].strip(),
                timeout_s=int(meta.get("timeout_s", 600)),
                control=bool(meta.get("control", False)),
                dir=meta_path.parent,
            )
        )
    return tasks


# ----------------------------------------------------------------------- workspace
def _git(ws: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "core.hooksPath=", *args], cwd=ws, capture_output=True, text=True, check=check
    )


def prepare(task: Task, condition: str, dest: Path) -> Path:
    """시작 상태를 만든다. 두 조건의 유일한 차이는 하네스 번들 설치 여부."""
    repo = dest / "repo"
    repo.mkdir(parents=True)
    shutil.copytree(task.dir / "project", repo, dirs_exist_ok=True)
    project_gitignore = task.dir / "project" / ".gitignore"
    project_ignore_text = (
        project_gitignore.read_text(encoding="utf-8") if project_gitignore.exists() else ""
    )

    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "eval@example.com")
    _git(repo, "config", "user.name", "Eval Runner")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "chore: 시작 상태")

    if condition == "harness":
        materialize_harness(repo)
        # 하네스 번들의 .gitignore 가 프로젝트 자신의 .gitignore 를 덮어쓰면 두 조건의
        # 시작 상태가 달라진다 → 프로젝트 규칙을 뒤에 붙여 픽스처를 동일하게 유지한다.
        if project_ignore_text:
            gi = repo / ".gitignore"
            existing = gi.read_text(encoding="utf-8") if gi.exists() else ""
            merged = existing.rstrip("\n") + "\n\n# --- 프로젝트 규칙 ---\n" + project_ignore_text
            gi.write_text(merged, encoding="utf-8")
        for pattern in (".scripts/*.sh", ".githooks/*"):
            for path in repo.glob(pattern):
                path.chmod(0o755)
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "chore: 하네스 설치")
        # 도구 무관 백스톱. 번들 문서가 지시하는 설치 절차(클론당 1회)를 러너가 대신 수행한다.
        subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=repo, check=True)

    setup = task.dir / "setup.sh"
    if setup.exists():
        subprocess.run(["bash", str(setup), str(repo)], check=True, capture_output=True)
    return repo


def apply_golden(task: Task, repo: Path) -> None:
    """골든 산출물을 덮어써 '완벽히 푼 상태' 를 만든다(채점기 자기검증용)."""
    solution = task.dir / "solution"
    skip = {"README.md", "grade.py", "heldout", "finish.sh"}
    for src in solution.rglob("*"):
        rel = src.relative_to(solution)
        if rel.parts[0] in skip:
            continue
        if src.is_file():
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            # copy2(mtime 보존) 금지: 골든과 결함 파일의 mtime(초 단위)·크기가 같으면
            # 기존 __pycache__ 가 유효하다고 판단돼 낡은 바이트코드가 계속 임포트된다.
            shutil.copyfile(src, repo / rel)
    purge_pycache(repo)
    finish = solution / "finish.sh"
    if finish.exists():
        subprocess.run(["bash", str(finish), str(repo)], check=True, capture_output=True)


def purge_pycache(repo: Path) -> None:
    """파일을 덮어쓴 뒤 남은 바이트코드 캐시를 지운다. 스테일 pyc 는 조용한 오판의 원인이다."""
    for cache in repo.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


# --------------------------------------------------------------------------- agent
def ensure_agent_toolchain(workroot: Path) -> Path:
    """에이전트 전용 venv(pytest·ruff)를 만든다. 실험 환경을 레포 상태로부터 격리한다.

    레포의 개발용 `.venv/bin` 을 에이전트 PATH 에 올리면 레포의 사정이 실험에 새어든다.
    실제로 레포 디렉터리명이 바뀌어 `.venv/bin/pytest` 의 shebang 이 죽어 있었고, 그 결과
    **하네스 조건만** Stop 게이트에서 `bad interpreter` 오류를 반복해 맞았다(바닐라 조건은
    verify.sh 가 없어서 영향 없음). 조건 하나만 망가지는 오염이라 A/B 결과가 무의미해진다.
    """
    venv = workroot / "agent-venv"
    python = venv / "bin" / "python"
    if not (venv / "bin" / "pytest").exists():
        subprocess.run(["uv", "venv", str(venv)], check=True, capture_output=True)
        subprocess.run(
            ["uv", "pip", "install", "--python", str(python), "pytest", "ruff", "pyyaml"],
            check=True,
            capture_output=True,
        )
    return venv


def agent_env(venv: Path) -> dict[str, str]:
    """에이전트에게 줄 환경변수. 레포 venv 를 PATH 에서 제거하고 전용 venv 를 앞에 둔다."""
    env = dict(os.environ)
    repo_venv = str(REPO / ".venv")
    parts = [p for p in env.get("PATH", "").split(os.pathsep) if p and not p.startswith(repo_venv)]
    env["PATH"] = os.pathsep.join([str(venv / "bin"), *parts])
    env.pop("VIRTUAL_ENV", None)
    env.pop("PYTHONPATH", None)  # 러너의 src/evals 경로가 작업공간에 새어들지 않게
    return env


def run_agent(
    task: Task, repo: Path, model: str, settings: Path, transcript: Path, env: dict[str, str]
) -> dict:
    cmd = [
        "claude",
        "-p",
        task.prompt,
        "--model",
        model,
        "--output-format",
        "stream-json",
        "--verbose",
        "--settings",
        str(settings),
        "--permission-mode",
        "acceptEdits",
        "--max-turns",
        "80",
    ]
    started = time.time()
    try:
        proc = subprocess.run(
            cmd, cwd=repo, capture_output=True, text=True, timeout=task.timeout_s, env=env
        )
        transcript.write_text(proc.stdout, encoding="utf-8")
        err = None if proc.returncode == 0 else f"exit={proc.returncode}: {proc.stderr[-400:]}"
    except subprocess.TimeoutExpired as exc:
        transcript.write_text(exc.stdout or "", encoding="utf-8")
        err = f"timeout after {task.timeout_s}s"
    meta = {"duration_s": round(time.time() - started, 1), "agent_error": err}
    for line in reversed(transcript.read_text(encoding="utf-8", errors="ignore").splitlines()):
        try:
            evt = json.loads(line)
        except ValueError:
            continue
        if evt.get("type") == "result":
            usage = evt.get("usage") or {}
            meta.update(
                num_turns=evt.get("num_turns"),
                cost_usd=evt.get("total_cost_usd"),
                tokens_in=(usage.get("input_tokens", 0) or 0)
                + (usage.get("cache_read_input_tokens", 0) or 0)
                + (usage.get("cache_creation_input_tokens", 0) or 0),
                tokens_out=usage.get("output_tokens"),
            )
            if evt.get("is_error"):
                meta["agent_error"] = str(evt.get("result"))[:400]
            break
    return meta


# --------------------------------------------------------------------------- grade
def grade(task: Task, repo: Path, transcript: Path) -> dict:
    env = dict(os.environ, EVAL_TRANSCRIPT=str(transcript))
    proc = subprocess.run(
        [sys.executable, str(task.dir / "solution" / "grade.py"), str(repo)],
        capture_output=True,
        text=True,
        env=env,
        timeout=600,
    )
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {
            "criteria": [],
            "score": 0.0,
            "fatal": True,
            "grader_error": (proc.stdout + proc.stderr)[-800:],
        }


# -------------------------------------------------------------------------- regrade
def regrade(source: Path) -> int:
    """이미 끝난 실행의 보존된 작업공간을 새 채점기로 다시 채점한다.

    에이전트 행동은 고정된 데이터다. 채점기 버그를 고쳤을 때 에이전트를 다시 돌릴 이유가 없다
    (비싸고, 실행 간 편차 때문에 비교도 흐려진다). 새 결과에는 `regraded_from` 을 남겨
    "어떤 실행을 어떤 채점기로 다시 읽었는지" 추적 가능하게 한다.
    """
    data = json.loads((source / "summary.json").read_text(encoding="utf-8"))
    tasks = {t.id: t for t in load_tasks(None)}
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_dir = RESULTS_DIR / f"{stamp}-agent"
    out_dir.mkdir(parents=True, exist_ok=True)

    for run in data["runs"]:
        slot = Path(run["workspace"])
        repo = slot / "repo"
        if not repo.exists():
            print(f"  건너뜀(작업공간 없음): {run['task']}/{run['condition']}")
            continue
        report = grade(tasks[run["task"]], repo, slot / "transcript.jsonl")
        before = run["score"]
        run["score"] = report.get("score", 0.0)
        run["fatal"] = report.get("fatal", False)
        run["criteria"] = report.get("criteria", [])
        changed = "" if before == run["score"] else f"  (이전 {before:.2f})"
        print(f"  {run['task']:26} {run['condition']:8} {run['score']:.2f}{changed}")
        (slot / "run.json").write_text(
            json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    data["regraded_from"] = source.name
    data["stamp"] = stamp
    (out_dir / "summary.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\n결과: {out_dir / 'summary.json'} (재채점 출처: {source.name})")
    return 0


# ---------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description="하네스 A/B 평가 러너")
    ap.add_argument("--mode", choices=("agent", "golden", "baseline"), default="agent")
    ap.add_argument("--tasks", help="쉼표 구분 태스크 id 접두사 (기본: 전체)")
    ap.add_argument("--conditions", default=",".join(CONDITIONS))
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--workroot", default=os.environ.get("EVAL_WORKROOT", ""))
    ap.add_argument(
        "--regrade",
        help="기존 결과 디렉터리를 새 채점기로 다시 채점한다(에이전트 재실행 없음)",
    )
    args = ap.parse_args()

    if args.regrade:
        return regrade(Path(args.regrade).resolve())

    tasks = load_tasks(args.tasks)
    if not tasks:
        print("태스크가 없다", file=sys.stderr)
        return 1
    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]

    stamp = time.strftime("%Y%m%d-%H%M%S")
    workroot = Path(args.workroot or (Path(os.environ.get("TMPDIR", "/tmp")) / "harness-eval"))
    workroot = workroot / f"{stamp}-{args.mode}"
    workroot.mkdir(parents=True, exist_ok=True)
    settings = workroot / "fair-settings.json"
    settings.write_text(json.dumps(FAIR_SETTINGS, indent=2), encoding="utf-8")
    # 에이전트 실행 환경은 레포와 분리한다(양 조건 동일). 자세한 이유는 ensure_agent_toolchain.
    env = agent_env(ensure_agent_toolchain(workroot)) if args.mode == "agent" else {}

    out_dir = RESULTS_DIR / f"{stamp}-{args.mode}"
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[RunResult] = []
    total = len(tasks) * len(conditions) * args.repeats
    n = 0
    for task in tasks:
        for condition in conditions:
            for repeat in range(1, args.repeats + 1):
                n += 1
                slot = workroot / task.id / condition / f"r{repeat}"
                slot.mkdir(parents=True, exist_ok=True)
                transcript = slot / "transcript.jsonl"
                print(
                    f"[{n}/{total}] {task.id} · {condition} · r{repeat} · {args.mode}", flush=True
                )
                repo = prepare(task, condition, slot)
                meta: dict = {"duration_s": 0.0}
                if args.mode == "golden":
                    apply_golden(task, repo)
                elif args.mode == "agent":
                    meta = run_agent(task, repo, args.model, settings, transcript, env)
                report = grade(task, repo, transcript)
                res = RunResult(
                    task=task.id,
                    condition=condition,
                    repeat=repeat,
                    mode=args.mode,
                    score=report.get("score", 0.0),
                    fatal=report.get("fatal", False),
                    criteria=report.get("criteria", []),
                    workspace=str(slot),
                    duration_s=meta.get("duration_s", 0.0),
                    num_turns=meta.get("num_turns"),
                    cost_usd=meta.get("cost_usd"),
                    tokens_in=meta.get("tokens_in"),
                    tokens_out=meta.get("tokens_out"),
                    agent_error=meta.get("agent_error") or report.get("grader_error"),
                )
                results.append(res)
                (slot / "run.json").write_text(
                    json.dumps(asdict(res), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
                flag = "☠ FATAL" if res.fatal else ""
                print(f"      → score={res.score:.2f} {flag} {res.agent_error or ''}", flush=True)

    payload = {
        "stamp": stamp,
        "mode": args.mode,
        "model": args.model,
        "repeats": args.repeats,
        "workroot": str(workroot),
        "runs": [asdict(r) for r in results],
    }
    (out_dir / "summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\n결과: {out_dir / 'summary.json'}")
    for r in results:
        print(f"  {r.task:26} {r.condition:8} {r.score:5.2f}{'  ☠' if r.fatal else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
