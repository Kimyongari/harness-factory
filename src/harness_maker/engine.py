"""치환 엔진: 스키마 로드 → 기본값 → 검증 → {{FILL}} 치환 → 도구별 어댑터 → zip.

설계 원칙:
- 템플릿(template/)은 프레임워크 중립 데이터다. 읽기만 한다.
- 스키마(survey.yaml)가 단일 진실 공급원. 스킵된 스텝은 default로 채운다.
- 어댑터가 중립 산출물을 타깃 도구(Claude Code / Codex) 포맷으로 변환한다.
- 시크릿은 .env로만, 설정 파일에는 환경변수 참조만.
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

PLACEHOLDER_RE = re.compile(r"\{\{FILL:([a-zA-Z0-9_.]+)\}\}")
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".sh", ".txt", ".json", ".toml", ".cfg", ".ini", ".py"}
RESERVED_PREFIXES = ("mcp.",)

# 브랜치 전략(설문 선택) → development SKILL.md 에 주입할 안내 블록.
# 키는 survey.{ko,en}.yaml 의 dev.branch_strategy 옵션 문자열과 정확히 일치해야 한다.
# {branch} 는 gh.default_branch 답변으로 치환된다.
BRANCH_STRATEGY_GUIDES: dict[str, str] = {
    # --- 한국어 ---
    "새 브랜치를 파서 작업": (
        "- 작업을 시작할 때 `{branch}`에서 새 브랜치를 만든다: `git switch -c <브랜치명>`"
        " (네이밍은 github-workflow 스킬 참고).\n"
        "- `{branch}`에 직접 커밋하지 않는다. 변경은 항상 브랜치에서 하고 완료되면 PR로 병합한다.\n"
        "- 끝나면 푸시 후 `gh pr create`로 PR을 연다."
    ),
    "git worktree로 작업": (
        "- 작업마다 별도 워크트리를 만들어 메인 체크아웃을 건드리지 않는다:"
        " `git worktree add ../<프로젝트>-<작업명> -b <브랜치명>`.\n"
        "- 해당 워크트리 디렉터리에서 작업·커밋하고, 끝나면 PR로 병합한 뒤 `git worktree remove`로 정리한다.\n"
        "- `{branch}` 체크아웃에서 직접 커밋하지 않는다. (여러 작업을 병렬로 격리할 때 유용하다.)"
    ),
    "기본 브랜치에 직접 작업": (
        "- 별도 브랜치 없이 `{branch}`에서 바로 작업하고 커밋한다(소규모·단독 프로젝트 방식).\n"
        "- 그래도 커밋은 사용자가 명시 요청할 때만 한다(github-workflow 스킬의 안전 수칙이 우선).\n"
        "- 푸시 전 `.scripts/verify.sh`를 통과시킨다. force push는 하지 않는다."
    ),
    # --- English ---
    "New branch": (
        "- Start each task by branching off `{branch}`: `git switch -c <branch-name>`"
        " (see the github-workflow skill for naming).\n"
        "- Never commit directly to `{branch}`. Work on a branch and merge via PR when done.\n"
        "- When finished, push and open a PR with `gh pr create`."
    ),
    "git worktree": (
        "- Create a separate worktree per task so the main checkout is untouched:"
        " `git worktree add ../<project>-<task> -b <branch-name>`.\n"
        "- Work and commit inside that worktree directory; when done, merge via PR and clean up"
        " with `git worktree remove`.\n"
        "- Don't commit directly in the `{branch}` checkout. (Handy for isolating parallel tasks.)"
    ),
    "Commit directly to the default branch": (
        "- Work and commit straight on `{branch}` with no feature branch (solo / small-project style).\n"
        "- Still commit only when the user explicitly asks (the github-workflow safety rules win).\n"
        "- Pass `.scripts/verify.sh` before pushing. Never force-push."
    ),
}


def _branch_strategy_guide(eff: dict[str, object]) -> str:
    """선택된 브랜치 전략에 맞는 안내 블록을 만든다. 매칭이 없으면 빈 문자열."""
    choice = str(eff.get("dev.branch_strategy") or "").strip()
    guide = BRANCH_STRATEGY_GUIDES.get(choice, "")
    branch = str(eff.get("gh.default_branch") or "main").strip() or "main"
    return guide.replace("{branch}", branch)


# 설문 라벨 → 내부 어댑터 id
TARGET_IDS = {"Claude Code": "claude-code", "Codex": "codex", "Cursor": "cursor"}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.S)


class ValidationError(Exception):
    """설문 답변이 스키마를 만족하지 못할 때."""


@dataclass(frozen=True)
class Field:
    key: str
    required: bool = False
    type: str = "string"
    question: str = ""
    default: object = ""


@dataclass
class Schema:
    fields: dict[str, Field] = field(default_factory=dict)
    placeholder_pattern: str = "{{FILL:KEY}}"
    required_block_build: bool = True

    @property
    def keys(self) -> set[str]:
        return set(self.fields)

    @property
    def required_keys(self) -> set[str]:
        return {k for k, f in self.fields.items() if f.required}


def load_schema(survey_path: str | Path) -> Schema:
    data = yaml.safe_load(Path(survey_path).read_text(encoding="utf-8")) or {}
    meta = data.get("meta", {})
    schema = Schema(
        placeholder_pattern=meta.get("placeholder_pattern", "{{FILL:KEY}}"),
        required_block_build=bool(meta.get("required_block_build", True)),
    )
    for step in data.get("steps", []):
        for f in step.get("fields", []):
            key = f["key"]
            schema.fields[key] = Field(
                key=key,
                required=bool(f.get("required", False)),
                type=f.get("type", "string"),
                question=f.get("question", ""),
                default=f.get("default", ""),
            )
    return schema


def load_catalog(catalog_path: str | Path) -> list[dict]:
    data = yaml.safe_load(Path(catalog_path).read_text(encoding="utf-8")) or {}
    return data.get("servers", [])


def load_checks(checks_path: str | Path) -> list[dict]:
    data = yaml.safe_load(Path(checks_path).read_text(encoding="utf-8")) or {}
    return data.get("checks", [])


def _is_empty(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, dict)):
        return len(value) == 0
    return False


def apply_defaults(answers: dict[str, object], schema: Schema) -> dict[str, object]:
    """누락/빈 값을 스키마 default로 채운 새 답변 dict. 스텝을 통째로 건너뛰면 여기서 기본값이 적용된다."""
    eff = dict(answers)
    for key, f in schema.fields.items():
        if _is_empty(eff.get(key)) and not _is_empty(f.default):
            eff[key] = f.default
        elif key not in eff:
            eff[key] = ""
    return eff


def validate(answers: dict[str, object], schema: Schema) -> None:
    errors: list[str] = []
    unknown = {k for k in answers if k not in schema.keys and not k.startswith(RESERVED_PREFIXES)}
    if unknown:
        errors.append(f"스키마에 없는 키가 답변에 포함됨: {sorted(unknown)}")
    if schema.required_block_build:
        eff = apply_defaults(answers, schema)
        for key in sorted(schema.required_keys):
            if _is_empty(eff.get(key)):
                errors.append(f"필수 값 누락: {key} ({schema.fields[key].question})")
    if errors:
        raise ValidationError("\n".join(errors))


def _render_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v).strip() for v in value if str(v).strip())
    return str(value).strip()


def substitute_text(text: str, answers: dict[str, object], schema: Schema) -> tuple[str, set[str]]:
    unknown_in_template: set[str] = set()

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in schema.keys:
            unknown_in_template.add(key)
            return match.group(0)
        return _render_value(answers.get(key))

    return PLACEHOLDER_RE.sub(repl, text), unknown_in_template


def generate_files(
    template_dir: str | Path, answers: dict[str, object], schema: Schema
) -> dict[str, bytes]:
    """template_dir를 순회하며 치환된 중립 파일 맵 {상대경로: bytes}를 만든다."""
    template_dir = Path(template_dir)
    out: dict[str, bytes] = {}
    drift: set[str] = set()
    for path in sorted(template_dir.rglob("*")):
        if path.is_dir() or path.name == ".DS_Store":
            continue
        rel = path.relative_to(template_dir).as_posix()
        if path.suffix in TEXT_SUFFIXES:
            rendered, unknown = substitute_text(path.read_text(encoding="utf-8"), answers, schema)
            drift |= unknown
            out[rel] = rendered.encode("utf-8")
        else:
            out[rel] = path.read_bytes()
    if drift:
        raise ValidationError(f"템플릿이 스키마에 없는 키를 참조함(드리프트): {sorted(drift)}.")
    return out


# ------------------------------------------------------------------------- MCP
def build_mcp(
    answers: dict[str, object], catalog: list[dict]
) -> tuple[list[dict], list[str], list[str]]:
    """선택된 서버(카탈로그 dict 목록), .env 값 줄, .env.example 줄을 반환한다."""
    selected = answers.get("mcp.servers") or []
    tokens = answers.get("mcp.tokens") or {}
    by_id = {s["id"]: s for s in catalog}
    servers: list[dict] = []
    env_values: list[str] = []
    env_example: list[str] = []
    for sid in selected:
        s = by_id.get(sid)
        if not s:
            continue
        servers.append(s)
        for e in s.get("env", []):
            var = e["var"]
            env_example.append(f"# {s['label']}: {e.get('label', var)}")
            env_example.append(f"{var}=")
            val = str(tokens.get(var, "")).strip()
            if val:
                env_values.append(f"{var}={val}")
    return servers, env_values, env_example


def _env_files(env_values: list[str], env_example: list[str]) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    if env_example:
        files[".env.example"] = ("\n".join(env_example) + "\n").encode("utf-8")
        files[".gitignore"] = b".env\n"
    if env_values:
        header = "# 자동 생성됨. 이 파일을 커밋하지 마세요(.gitignore에 포함).\n"
        files[".env"] = (header + "\n".join(env_values) + "\n").encode("utf-8")
    return files


# ----------------------------------------------------------------- 훅 스크립트
def _hook_script(stage: str, commands: list[str]) -> bytes:
    """선택된 검사 명령들로 stage 훅 스크립트를 생성한다."""
    lines = [
        "#!/usr/bin/env bash",
        f"# {stage} hook — 설문에서 고른 검사 프리셋으로 생성됨",
        "set -uo pipefail",
        "",
        "fail=0",
    ]
    if not commands:
        lines.append(f'echo "[{stage}] 선택된 검사가 없습니다."')
    else:
        for cmd in commands:
            lines += ["", f'echo "→ {cmd}"', f"{cmd} || fail=1"]
    lines += [
        "",
        'if [ "$fail" -ne 0 ]; then',
        f'  echo "[{stage}] 실패 — 위 출력을 확인하세요"; exit 1',
        "fi",
        f'echo "[{stage}] 통과"',
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def build_hook_scripts(answers: dict[str, object], checks: list[dict]) -> dict[str, bytes]:
    """선택된 프리셋으로 .scripts/pre-commit.sh / post-commit.sh 를 생성한다."""
    by_id = {c["id"]: c for c in checks}
    out: dict[str, bytes] = {}
    for stage, key in (("pre-commit", "hooks.pre_commit"), ("post-commit", "hooks.post_commit")):
        ids = answers.get(key) or []
        cmds = [by_id[i]["command"] for i in ids if i in by_id]
        out[f".scripts/{stage}.sh"] = _hook_script(stage, cmds)
    return out


# --------------------------------------------------------------- git 훅 (도구 무관)
# Claude Code / Codex 는 런타임 훅(PreToolUse/Stop)으로 강제하지만 Cursor 등 런타임
# 훅이 없는 도구는 .scripts/* 를 자동 실행하지 않는다. git 훅은 도구와 무관하게
# `git commit` / `git push` 시점에 발동하므로, 어떤 에이전트가 커밋하든 동일하게
# 검증을 강제하는 백스톱이 된다.  설치(클론마다 1회): git config core.hooksPath .githooks
_GIT_PRE_COMMIT = """#!/usr/bin/env bash
# 도구 무관 git pre-commit 훅 — Cursor 처럼 런타임 훅이 없는 도구에서도 강제된다.
# 설치(클론마다 1회):  git config core.hooksPath .githooks
# 빠른 검사(경계 + 린트/포맷/타입체크)만 돌린다. 무거운 테스트는 pre-push 로.
set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fail=0
[ -x "$ROOT/.scripts/check-boundaries.sh" ] && { "$ROOT/.scripts/check-boundaries.sh" || fail=1; }
[ -f "$ROOT/.scripts/pre-commit.sh" ] && { bash "$ROOT/.scripts/pre-commit.sh" || fail=1; }
if [ "$fail" -ne 0 ]; then
  echo "[git pre-commit] 검사 실패 — 위 출력을 고친 뒤 다시 커밋하세요. (원인 미해결 시 --no-verify 로 우회하지 말 것)" >&2
  exit 1
fi
"""


def _git_pre_push(protected: str) -> str:
    """보호 브랜치로의 강제(non-fast-forward) 푸시를 거부하고, 무거운 검사를 돌리는 pre-push 훅."""
    return f"""#!/usr/bin/env bash
# 도구 무관 git pre-push 훅 — 어떤 에이전트가 푸시하든 발동한다.
# 설치(클론마다 1회):  git config core.hooksPath .githooks
# 1) 보호 브랜치 '{protected}' 로의 강제(히스토리 재작성) 푸시를 거부.
# 2) 무거운 검사(테스트 등)를 실행.
set -uo pipefail
PROTECTED="{protected}"
ZERO="0000000000000000000000000000000000000000"

# git 은 push 대상 ref 들을 stdin 으로 준다: <local ref> <local sha> <remote ref> <remote sha>
while read -r _local_ref _local_sha remote_ref remote_sha; do
  [ -z "${{remote_ref:-}}" ] && continue
  branch="${{remote_ref#refs/heads/}}"
  [ "$branch" != "$PROTECTED" ] && continue
  # 새 브랜치 생성/삭제는 통과. 기존 ref 가 local 의 조상이 아니면 = 강제/재작성 푸시.
  [ "$remote_sha" = "$ZERO" ] && continue
  [ "$_local_sha" = "$ZERO" ] && continue
  if ! git merge-base --is-ancestor "$remote_sha" "$_local_sha" 2>/dev/null; then
    echo "[git pre-push] 거부: 보호 브랜치 '$PROTECTED' 로의 강제(non-fast-forward) 푸시." >&2
    echo "   되돌릴 수 없는 작업입니다. 정말 필요하면 사용자에게 명시적으로 확인받으세요." >&2
    exit 1
  fi
done

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
if [ -f "$ROOT/.scripts/post-commit.sh" ]; then
  bash "$ROOT/.scripts/post-commit.sh" || {{
    echo "[git pre-push] 검사 실패 — 위 출력을 고친 뒤 다시 푸시하세요." >&2
    exit 1
  }}
fi
"""


def build_git_hooks(answers: dict[str, object]) -> dict[str, bytes]:
    """core.hooksPath 로 설치하는 도구 무관 git 훅(.githooks/pre-commit, pre-push)을 생성한다."""
    protected = str(answers.get("gh.default_branch") or "main").strip() or "main"
    return {
        ".githooks/pre-commit": _GIT_PRE_COMMIT.encode("utf-8"),
        ".githooks/pre-push": _git_pre_push(protected).encode("utf-8"),
    }


def _claude_mcp_json(servers: list[dict]) -> bytes:
    cfg = {"mcpServers": {s["id"]: s["config"] for s in servers}}
    return (json.dumps(cfg, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _claude_settings_json() -> bytes:
    """Claude Code의 결정론적 훅 설정.

    LLM 판단이 아니라 Claude Code 런타임이 자동 호출한다:
    - PreToolUse(Bash)  → .scripts/guard-bash.sh : 파괴적 명령/never_touch 위반을
      도구 실행 전에 차단(permissionDecision="deny").
    - PostToolUse(Edit|Write|MultiEdit) → .scripts/pre-commit.sh : 파일 편집 직후 린트/포맷.
    - Stop → .scripts/verify.sh : 응답 종료 직전 전체 검증 파이프라인.

    참고: https://code.claude.com/docs/en/hooks
    """
    cfg = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": "bash .scripts/guard-bash.sh"}],
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "Edit|Write|MultiEdit",
                    "hooks": [{"type": "command", "command": "bash .scripts/pre-commit.sh"}],
                }
            ],
            "Stop": [
                {
                    "matcher": "",
                    "hooks": [{"type": "command", "command": "bash .scripts/verify.sh"}],
                }
            ],
        }
    }
    return (json.dumps(cfg, indent=2) + "\n").encode("utf-8")


def _toml_str(x: object) -> str:
    return json.dumps(str(x))  # TOML 기본 문자열과 호환되는 큰따옴표 이스케이프


def _codex_toml(servers: list[dict]) -> bytes:
    lines = [
        "# Codex 설정. 신뢰된 프로젝트라면 이 파일을 .codex/config.toml 로,",
        "# 그 외에는 ~/.codex/config.toml 에 병합하세요.",
        "",
        "# 안전 정책 — OS 수준 강제(워크스페이스 밖 쓰기/네트워크 자동 차단).",
        "# LLM 프롬프트가 아니라 Codex 런타임 + 커널이 enforce 합니다.",
        'sandbox_mode = "workspace-write"     # read-only / workspace-write / danger-full-access',
        'approval_policy = "on-request"       # untrusted / on-request / never',
        "",
        "# 결정론적 훅 — Claude Code 의 hooks 와 동일한 이벤트 스키마.",
        "# Codex 는 tool_name 을 canonical 이름('Bash')으로 정규화하고 tool_input.command 를",
        "# 문자열로 주며, deny 출력도 Claude 와 동일(permissionDecision='deny')하므로",
        "# guard-bash.sh 가 그대로 동작한다(별도 어댑터 불필요).",
        "# 런타임이 자동 호출하므로 LLM 이 끄지 못한다.",
        "# 주의: 훅은 session cwd 에서 실행된다. 상대경로 'bash .scripts/...' 가 풀리도록",
        "#       codex 는 프로젝트(git) 루트에서 실행하세요.",
        "# 참고: https://developers.openai.com/codex/hooks",
        "",
        "[[hooks.PreToolUse]]",
        'matcher = "Bash"',
        "",
        "[[hooks.PreToolUse.hooks]]",
        'type = "command"',
        'command = "bash .scripts/guard-bash.sh"',
        "",
        "[[hooks.Stop]]",
        "",
        "[[hooks.Stop.hooks]]",
        'type = "command"',
        'command = "bash .scripts/verify.sh"',
        "",
    ]
    if servers:
        lines += [
            "# MCP 서버. 토큰은 .env 에 있습니다.",
            "# codex 실행 전 환경변수로 로드하세요:  set -a; source .env; set +a",
            "",
        ]
    for s in servers:
        cfg = s["config"]
        lines.append(f"[mcp_servers.{s['id']}]")
        lines.append(f"command = {_toml_str(cfg['command'])}")
        args = cfg.get("args", [])
        lines.append("args = [" + ", ".join(_toml_str(a) for a in args) + "]")
        env_vars = [e["var"] for e in s.get("env", [])]
        if env_vars:
            lines.append("env_vars = [" + ", ".join(_toml_str(v) for v in env_vars) + "]")
        lines.append("")
    return ("\n".join(lines) + "\n").encode("utf-8")


# ----------------------------------------------------------------- Cursor 헬퍼
def _split_frontmatter(text: str) -> tuple[dict, str]:
    """SKILL.md 등의 YAML frontmatter를 (메타, 본문)으로 분리한다."""
    m = FRONTMATTER_RE.match(text)
    if m:
        return (yaml.safe_load(m.group(1)) or {}), m.group(2)
    return {}, text


def _mdc(description: str, body: str, always: bool = False, globs: str = "") -> str:
    """Cursor .mdc 파일(frontmatter + 본문)을 만든다.

    Cursor 규칙의 결정론적 적용:
    - alwaysApply: true                → 항상 적용 (가장 결정론적)
    - alwaysApply: false + globs       → 파일 매치 시 자동 첨부 (결정론적)
    - alwaysApply: false + description → 모델이 description 을 보고 판단 (LLM-judgment)
    참고: https://cursor.com/docs/context/rules
    """
    fm = [
        "---",
        f"description: {json.dumps(description, ensure_ascii=False)}",
        f"globs: {globs}",
        f"alwaysApply: {'true' if always else 'false'}",
        "---",
        "",
        body.rstrip("\n"),
    ]
    return "\n".join(fm) + "\n"


# 스킬 → Cursor globs 매핑.  파일 컨텍스트에 매칭되는 스킬은 자동 첨부(결정론적).
# 매핑이 없는 스킬은 description 기반(LLM-judgment) 그대로 둔다.
SKILL_GLOBS: dict[str, str] = {
    "development": (
        "**/*.py,**/*.ts,**/*.tsx,**/*.js,**/*.jsx,**/*.go,**/*.rs,"
        "**/*.java,**/*.kt,**/*.rb,**/*.php,**/*.cs,**/*.c,**/*.cpp,"
        "**/*.h,**/*.hpp,**/*.swift,**/*.scala,**/*.sh,**/*.sql"
    ),
    "doc-writing": "**/*.md,**/*.mdc,**/*.rst,**/*.txt,README*,CHANGELOG*",
    # github-workflow / web-research : 파일 범위가 없어 description 기반 유지.
}


def _rewrite_skill_paths_cursor(text: str) -> str:
    """본문의 .skills/<name>/SKILL.md 참조를 Cursor 규칙 경로로 바꾼다."""
    text = re.sub(r"\.skills/([a-zA-Z0-9_-]+)/SKILL\.md", r".cursor/rules/\1.mdc", text)
    return text.replace(".skills/", ".cursor/rules/")


# --------------------------------------------------------------------- 어댑터
def adapt_target(
    target: str,
    base: dict[str, bytes],
    servers: list[dict],
    env_values: list[str],
    env_example: list[str],
) -> dict[str, bytes]:
    """중립 파일 맵을 타깃 도구 포맷으로 변환한다."""
    files = dict(base)
    files.update(_env_files(env_values, env_example))

    if target == "claude-code":
        # AGENT.md → CLAUDE.md, .skills/ → .claude/skills/ (경로 참조까지 일괄 치환)
        out: dict[str, bytes] = {}
        for path, content in files.items():
            newpath = path
            if path.startswith(".skills/"):
                newpath = ".claude/skills/" + path[len(".skills/") :]
            if path == "AGENT.md":
                newpath = "CLAUDE.md"
            data = content
            if newpath.rsplit(".", 1)[-1] in {"md", "yaml", "yml", "txt", "json", "toml"}:
                try:
                    data = (
                        content.decode("utf-8")
                        .replace(".skills/", ".claude/skills/")
                        .encode("utf-8")
                    )
                except UnicodeDecodeError:
                    pass
            out[newpath] = data
        # Claude Code의 결정론적 훅 — 항상 포함(런타임이 강제 실행).
        out[".claude/settings.json"] = _claude_settings_json()
        if servers:
            out[".mcp.json"] = _claude_mcp_json(servers)
        return out

    if target == "codex":
        # AGENT.md → AGENTS.md, 스킬은 .skills/ 그대로 두고 AGENTS.md가 참조한다.
        # 안전 정책(sandbox/approval)은 OS 수준 강제이므로 항상 포함한다.
        out = {}
        for path, content in files.items():
            out["AGENTS.md" if path == "AGENT.md" else path] = content
        out[".codex/config.toml"] = _codex_toml(servers)
        return out

    if target == "cursor":
        # AGENT.md → .cursor/rules/00-overview.mdc(always), 각 스킬 → .cursor/rules/<name>.mdc(agent-requested)
        out = {}
        for path, content in files.items():
            if path == "AGENT.md" or path.startswith(".skills/"):
                continue
            out[path] = content

        overview = _rewrite_skill_paths_cursor(files["AGENT.md"].decode("utf-8"))
        out[".cursor/rules/00-overview.mdc"] = _mdc(
            "프로젝트 전반 규칙과 작업 라우팅. 모든 대화에 항상 적용.", overview, always=True
        ).encode("utf-8")

        for path, content in files.items():
            if not path.startswith(".skills/"):
                continue
            name = path.split("/")[1]
            if path.endswith("/SKILL.md"):
                meta, body = _split_frontmatter(content.decode("utf-8"))
                # 파일 범위가 명확한 스킬은 globs 로 자동 첨부(결정론적).
                # 매핑이 없는 스킬은 description 기반(LLM 판단)으로 둔다.
                globs = SKILL_GLOBS.get(name, "")
                out[f".cursor/rules/{name}.mdc"] = _mdc(
                    str(meta.get("description", name)),
                    body.strip(),
                    always=False,
                    globs=globs,
                ).encode("utf-8")
            else:  # 스킬 리소스 파일은 같은 이름의 하위 폴더로 보존
                rest = path[len(".skills/") :]
                out[f".cursor/rules/{rest}"] = content

        if servers:
            out[".cursor/mcp.json"] = _claude_mcp_json(servers)  # mcpServers 형식 동일
        return out

    return files


def _selected_targets(answers: dict[str, object]) -> list[str]:
    raw = answers.get("target.tools") or []
    if isinstance(raw, str):
        raw = [raw]
    ids = [TARGET_IDS.get(x, x) for x in raw]
    return ids or ["claude-code"]


def generate_bundle(
    template_dir: str | Path,
    answers: dict[str, object],
    schema: Schema,
    catalog: list[dict] | None = None,
    checks: list[dict] | None = None,
) -> dict[str, bytes]:
    """검증 → 기본값 → 치환 → 훅 스크립트 → 타깃별 어댑터. 타깃이 여러 개면 <target>/ 하위로 나눈다."""
    validate(answers, schema)
    eff = apply_defaults(answers, schema)
    eff["dev.branch_strategy_guide"] = _branch_strategy_guide(eff)
    base = generate_files(template_dir, eff, schema)
    base.update(build_git_hooks(eff))  # 도구 무관 git 훅(core.hooksPath) — 모든 타깃에 포함
    if checks:
        base.update(build_hook_scripts(eff, checks))  # 선택된 프리셋으로 훅 스크립트 생성
    servers, env_values, env_example = build_mcp(answers, catalog or [])
    targets = _selected_targets(answers)

    result: dict[str, bytes] = {}
    for t in targets:
        adapted = adapt_target(t, base, servers, env_values, env_example)
        if len(targets) == 1:
            result.update(adapted)
        else:
            for k, v in adapted.items():
                result[f"{t}/{k}"] = v
    return result


def build_zip(files: dict[str, bytes], root_dir: str = "") -> bytes:
    buf = io.BytesIO()
    prefix = (root_dir.rstrip("/") + "/") if root_dir else ""
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel, content in sorted(files.items()):
            name = prefix + rel
            # 셸 스크립트와 git 훅(.githooks/*, 확장자 없음)은 실행 권한 부여
            if rel.endswith(".sh") or "/.githooks/" in f"/{rel}":
                info = zipfile.ZipInfo(name)
                info.external_attr = 0o755 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, content)
            else:
                zf.writestr(name, content)
    return buf.getvalue()


def generate_zip(
    template_dir: str | Path,
    answers: dict[str, object],
    schema: Schema,
    catalog: list[dict] | None = None,
    checks: list[dict] | None = None,
    root_dir: str = "harness",
) -> bytes:
    return build_zip(
        generate_bundle(template_dir, answers, schema, catalog, checks), root_dir=root_dir
    )


# --------------------------------------------------------------------------- CLI
def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="설문 답변으로 하네스 zip을 생성한다.")
    parser.add_argument("--lang", default="ko", choices=["ko", "en"])
    parser.add_argument("--survey", default=None, help="기본: survey.<lang>.yaml")
    parser.add_argument("--catalog", default="mcp_catalog.yaml")
    parser.add_argument("--checks", default="checks_catalog.yaml")
    parser.add_argument("--template", default=None, help="기본: template/<lang>")
    parser.add_argument("--answers", required=True)
    parser.add_argument("--out", default="harness.zip")
    args = parser.parse_args()
    survey_path = args.survey or f"survey.{args.lang}.yaml"
    template_dir = args.template or f"template/{args.lang}"

    schema = load_schema(survey_path)
    catalog = load_catalog(args.catalog) if Path(args.catalog).exists() else []
    checks = load_checks(args.checks) if Path(args.checks).exists() else []
    answers = json.loads(Path(args.answers).read_text(encoding="utf-8"))
    try:
        data = generate_zip(template_dir, answers, schema, catalog=catalog, checks=checks)
    except ValidationError as e:
        print(f"[generate] 검증 실패:\n{e}")
        return 1
    Path(args.out).write_bytes(data)
    print(f"[generate] 생성 완료 → {args.out} ({len(data)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
