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

from harness import DEFAULT_TARGET, TARGETS, materialize_harness, no_git_env  # noqa: E402

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


# --------------------------------------------------------------------------- 러너
# 타깃마다 헤드리스 실행 방법이 다르다. 하네스 쪽(생성·훅·검사)은 세 타깃이 공유하지만
# "에이전트를 어떻게 띄우는가" 는 도구 CLI 마다 달라서 여기서 갈린다.
#
# `verified` 는 **이 저장소에서 실제로 돌려 확인했는가** 다. 정직하게 표시한다 —
# 미설치 CLI 의 인자·트랜스크립트 스키마는 문서를 근거로 적었을 뿐 실측하지 않았다.
@dataclass(frozen=True)
class Runner:
    target: str
    binary: str
    verified: bool
    note: str

    def build(self, prompt: str, model: str, settings: Path) -> list[str]:
        raise NotImplementedError


@dataclass(frozen=True)
class ClaudeCodeRunner(Runner):
    def build(self, prompt: str, model: str, settings: Path) -> list[str]:
        return [
            self.binary,
            "-p",
            prompt,
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


@dataclass(frozen=True)
class CodexRunner(Runner):
    def build(self, prompt: str, model: str, settings: Path) -> list[str]:
        # Codex 의 권한 경계는 CLI 플래그(샌드박스/승인 정책)로 준다 — `--settings` 상당물이 없다.
        return [
            self.binary,
            "exec",
            prompt,
            "--model",
            model,
            "--json",
            "--sandbox",
            "workspace-write",
        ]


@dataclass(frozen=True)
class CursorRunner(Runner):
    def build(self, prompt: str, model: str, settings: Path) -> list[str]:
        return [
            self.binary,
            "-p",
            prompt,
            "--model",
            model,
            "--output-format",
            "stream-json",
            "--force",
        ]


RUNNERS: dict[str, Runner] = {
    "claude-code": ClaudeCodeRunner(
        target="claude-code",
        binary="claude",
        verified=True,
        note="`--settings` 로 양 조건에 동일한 권한 허용목록을 주입한다(공정성 장치).",
    ),
    "codex": CodexRunner(
        target="codex",
        binary="codex",
        verified=False,
        note="권한은 `--sandbox workspace-write` 로 준다. `--settings` 상당물이 없어 "
        "허용목록 주입 방식이 Claude Code 와 다르다 — 조건 간에는 동일하므로 A/B 는 공정하다.",
    ),
    "cursor": CursorRunner(
        target="cursor",
        binary="cursor-agent",
        verified=False,
        note="cursor-agent 헤드리스 실행. 트랜스크립트 스키마를 실측하지 못했으므로 "
        "프로세스·정직성 축 채점은 형식 무관 추출기에 의존한다.",
    ),
}


def runner_status(target: str) -> tuple[Runner, bool, str]:
    """(러너, 실행 가능 여부, 사유)."""
    runner = RUNNERS[target]
    if shutil.which(runner.binary) is None:
        return runner, False, f"CLI '{runner.binary}' 를 PATH 에서 찾을 수 없다"
    if not runner.verified:
        return runner, True, f"주의: '{runner.binary}' 실행 인자는 이 저장소에서 실측되지 않았다"
    return runner, True, "ok"


@dataclass
class RunResult:
    task: str
    condition: str
    target: str
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
# 태스크가 선언하는 "하네스가 차이를 만들 기제". skill-text 는 결정론적 검사 없이
# 지시문 문장에만 의존한다는 뜻이고, 그 태스크의 무승부는 예상된 결과다.
MECHANISMS = {"guard-bash", "verify-gate", "git-hook", "scaffold", "skill-text", "none"}


@dataclass
class Task:
    id: str
    title: str
    axis: str
    mechanism: str
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
                mechanism=meta.get("mechanism", "skill-text"),
                prompt=meta["prompt"].strip(),
                timeout_s=int(meta.get("timeout_s", 600)),
                control=bool(meta.get("control", False)),
                dir=meta_path.parent,
            )
        )
    return tasks


# ----------------------------------------------------------------------- workspace
# 작업공간을 만지는 모든 서브프로세스는 no_git_env() 위에서 돈다. git 훅(pre-push 의
# pytest)이 물려주는 GIT_DIR 이 상속되면 작업공간의 git 명령이 바깥 레포를 조작한다.
def _git(ws: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "core.hooksPath=", *args],
        cwd=ws,
        capture_output=True,
        text=True,
        check=check,
        env=no_git_env(),
    )


def prepare(task: Task, condition: str, dest: Path, target: str = DEFAULT_TARGET) -> Path:
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
        materialize_harness(repo, target=target)
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
        subprocess.run(
            ["git", "config", "core.hooksPath", ".githooks"],
            cwd=repo,
            check=True,
            env=no_git_env(),
        )

    setup = task.dir / "setup.sh"
    if setup.exists():
        subprocess.run(
            ["bash", str(setup), str(repo)], check=True, capture_output=True, env=no_git_env()
        )
    # 채점 기준선. 하네스 조건은 설치 커밋 때문에 시작 커밋 수가 다르다(2 vs 1) —
    # 채점기가 커밋 수 절대값으로 "커밋했는가" 를 판정하면 하네스 쪽만 게이트가 공짜로
    # 통과하는 조건 편향이 생긴다. 기준값은 에이전트가 손댈 수 없는 작업공간 밖에 둔다
    # (setup.sh 가 남기는 *-sha.txt 와 같은 자리).
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    (dest / "baseline-head.txt").write_text(head + "\n", encoding="utf-8")
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
        subprocess.run(
            ["bash", str(finish), str(repo)], check=True, capture_output=True, env=no_git_env()
        )


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
    env = no_git_env()
    repo_venv = str(REPO / ".venv")
    parts = [p for p in env.get("PATH", "").split(os.pathsep) if p and not p.startswith(repo_venv)]
    env["PATH"] = os.pathsep.join([str(venv / "bin"), *parts])
    env.pop("VIRTUAL_ENV", None)
    env.pop("PYTHONPATH", None)  # 러너의 src/evals 경로가 작업공간에 새어들지 않게
    return env


def run_agent(
    task: Task,
    repo: Path,
    model: str,
    settings: Path,
    transcript: Path,
    env: dict[str, str],
    target: str = DEFAULT_TARGET,
) -> dict:
    cmd = RUNNERS[target].build(task.prompt, model, settings)
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
    env = dict(no_git_env(), EVAL_TRANSCRIPT=str(transcript))
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
        run.setdefault("target", data.get("target", DEFAULT_TARGET))
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
    ap.add_argument(
        "--target",
        default=DEFAULT_TARGET,
        choices=sorted(TARGETS),
        help="평가할 하네스 타깃. 하네스 생성물과 에이전트 CLI 가 함께 바뀐다.",
    )
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

    if args.mode == "agent":
        runner, runnable, why = runner_status(args.target)
        if not runnable:
            print(f"[{args.target}] 실행 불가 — {why}", file=sys.stderr)
            print(f"  {runner.note}", file=sys.stderr)
            return 2
        if why != "ok":
            print(f"[{args.target}] {why}")
        print(f"러너: {runner.binary} (target={args.target}) — {runner.note}")

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
                repo = prepare(task, condition, slot, target=args.target)
                meta: dict = {"duration_s": 0.0}
                if args.mode == "golden":
                    apply_golden(task, repo)
                elif args.mode == "agent":
                    meta = run_agent(
                        task, repo, args.model, settings, transcript, env, target=args.target
                    )
                report = grade(task, repo, transcript)
                res = RunResult(
                    task=task.id,
                    condition=condition,
                    target=args.target,
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
        "target": args.target,
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
