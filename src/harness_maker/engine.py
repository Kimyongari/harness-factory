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


def _claude_mcp_json(servers: list[dict]) -> bytes:
    cfg = {"mcpServers": {s["id"]: s["config"] for s in servers}}
    return (json.dumps(cfg, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _toml_str(x: object) -> str:
    return json.dumps(str(x))  # TOML 기본 문자열과 호환되는 큰따옴표 이스케이프


def _codex_toml(servers: list[dict]) -> bytes:
    lines = [
        "# Codex MCP 설정.",
        "# 신뢰된 프로젝트라면 이 파일을 .codex/config.toml 로 두거나, ~/.codex/config.toml 에 병합하세요.",
        "# 토큰은 .env 에 있습니다. codex 실행 전 환경변수로 로드하세요:  set -a; source .env; set +a",
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
    """Cursor .mdc 파일(frontmatter + 본문)을 만든다."""
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
        if servers:
            out[".mcp.json"] = _claude_mcp_json(servers)
        return out

    if target == "codex":
        # AGENT.md → AGENTS.md, 스킬은 .skills/ 그대로 두고 AGENTS.md가 참조한다.
        out = {}
        for path, content in files.items():
            out["AGENTS.md" if path == "AGENT.md" else path] = content
        if servers:
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
                out[f".cursor/rules/{name}.mdc"] = _mdc(
                    str(meta.get("description", name)), body.strip(), always=False
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
) -> dict[str, bytes]:
    """검증 → 기본값 → 치환 → 타깃별 어댑터. 타깃이 여러 개면 <target>/ 하위로 나눈다."""
    validate(answers, schema)
    eff = apply_defaults(answers, schema)
    base = generate_files(template_dir, eff, schema)
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
            zf.writestr(prefix + rel, content)
    return buf.getvalue()


def generate_zip(
    template_dir: str | Path,
    answers: dict[str, object],
    schema: Schema,
    catalog: list[dict] | None = None,
    root_dir: str = "harness",
) -> bytes:
    return build_zip(generate_bundle(template_dir, answers, schema, catalog), root_dir=root_dir)


# --------------------------------------------------------------------------- CLI
def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="설문 답변으로 하네스 zip을 생성한다.")
    parser.add_argument("--lang", default="ko", choices=["ko", "en"])
    parser.add_argument("--survey", default=None, help="기본: survey.<lang>.yaml")
    parser.add_argument("--catalog", default="mcp_catalog.yaml")
    parser.add_argument("--template", default=None, help="기본: template/<lang>")
    parser.add_argument("--answers", required=True)
    parser.add_argument("--out", default="harness.zip")
    args = parser.parse_args()
    survey_path = args.survey or f"survey.{args.lang}.yaml"
    template_dir = args.template or f"template/{args.lang}"

    schema = load_schema(survey_path)
    catalog = load_catalog(args.catalog) if Path(args.catalog).exists() else []
    answers = json.loads(Path(args.answers).read_text(encoding="utf-8"))
    try:
        data = generate_zip(template_dir, answers, schema, catalog=catalog)
    except ValidationError as e:
        print(f"[generate] 검증 실패:\n{e}")
        return 1
    Path(args.out).write_bytes(data)
    print(f"[generate] 생성 완료 → {args.out} ({len(data)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
