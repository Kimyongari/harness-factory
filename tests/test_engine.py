import io
import json
import zipfile
from pathlib import Path

import pytest

from harness_maker.engine import (
    ValidationError,
    adapt_target,
    apply_defaults,
    build_mcp,
    generate_bundle,
    generate_files,
    generate_zip,
    load_catalog,
    load_schema,
    substitute_text,
    validate,
)

ROOT = Path(__file__).resolve().parents[1]
SURVEY = ROOT / "survey.yaml"
CATALOG = ROOT / "mcp_catalog.yaml"
TEMPLATE = ROOT / "template"


@pytest.fixture
def schema():
    return load_schema(SURVEY)


@pytest.fixture
def catalog():
    return load_catalog(CATALOG)


@pytest.fixture
def answers():
    return json.loads((ROOT / "tests" / "sample_answers.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 스키마/검증
def test_required_minimized(schema):
    assert schema.required_keys <= {
        "target.tools", "project.name", "project.description",
        "project.language", "project.package_manager", "profile.role",
    }


def test_validate_passes(schema, answers):
    validate(answers, schema)


def test_validate_fails_on_missing_required(schema, answers):
    answers.pop("project.name")
    with pytest.raises(ValidationError) as e:
        validate(answers, schema)
    assert "project.name" in str(e.value)


def test_mcp_keys_not_rejected(schema):
    validate(
        {
            "target.tools": ["Claude Code"], "project.name": "x", "project.description": "y",
            "project.language": "Python", "project.package_manager": "pip", "profile.role": "backend",
            "mcp.servers": ["github"], "mcp.tokens": {"GITHUB_PERSONAL_ACCESS_TOKEN": "t"},
        },
        schema,
    )


def test_defaults_applied_when_step_skipped(schema):
    raw = {
        "target.tools": ["Claude Code"], "project.name": "x", "project.description": "y",
        "project.language": "Python", "project.package_manager": "pip", "profile.role": "backend",
    }
    eff = apply_defaults(raw, schema)
    assert eff["docs.language"] == "한국어"
    assert eff["gh.default_branch"] == "main"
    assert ".env" in eff["dev.never_touch"]


# ---------------------------------------------------------------- 치환
def test_substitute_joins_lists(schema):
    out, _ = substitute_text("{{FILL:dev.never_touch}}", {"dev.never_touch": [".env", "x/"]}, schema)
    assert out == ".env, x/"


def test_no_leftover_placeholders_and_no_drift(schema, answers):
    eff = apply_defaults(answers, schema)
    files = generate_files(TEMPLATE, eff, schema)
    assert not [p for p, c in files.items() if b"{{FILL:" in c]


# ---------------------------------------------------------------- MCP
def test_build_mcp(catalog, answers):
    servers, env_values, env_example = build_mcp(answers, catalog)
    assert [s["id"] for s in servers] == ["github", "fetch", "sequential-thinking"]
    assert any("GITHUB_PERSONAL_ACCESS_TOKEN=ghp_example_token_123" == v for v in env_values)


# ---------------------------------------------------------------- 어댑터
def test_claude_adapter_layout(schema, catalog, answers):
    eff = apply_defaults(answers, schema)
    base = generate_files(TEMPLATE, eff, schema)
    servers, ev, ex = build_mcp(answers, catalog)
    out = adapt_target("claude-code", base, servers, ev, ex)
    assert "CLAUDE.md" in out and "AGENT.md" not in out
    assert ".claude/skills/development/SKILL.md" in out
    assert ".mcp.json" in out
    # CLAUDE.md의 경로 참조가 .claude/skills/ 로 치환됐는지
    assert b".claude/skills/" in out["CLAUDE.md"]
    assert b"\n## " in out["CLAUDE.md"]


def test_codex_adapter_layout(schema, catalog, answers):
    eff = apply_defaults(answers, schema)
    base = generate_files(TEMPLATE, eff, schema)
    servers, ev, ex = build_mcp(answers, catalog)
    out = adapt_target("codex", base, servers, ev, ex)
    assert "AGENTS.md" in out and "AGENT.md" not in out
    assert ".skills/development/SKILL.md" in out          # 스킬은 그대로
    assert ".codex/config.toml" in out
    toml = out[".codex/config.toml"].decode("utf-8")
    assert "[mcp_servers.github]" in toml
    assert 'env_vars = ["GITHUB_PERSONAL_ACCESS_TOKEN"]' in toml


def test_cursor_adapter_layout(schema, catalog, answers):
    eff = apply_defaults(answers, schema)
    base = generate_files(TEMPLATE, eff, schema)
    servers, ev, ex = build_mcp(answers, catalog)
    out = adapt_target("cursor", base, servers, ev, ex)
    assert "AGENT.md" not in out
    assert ".cursor/rules/00-overview.mdc" in out
    assert ".cursor/rules/development.mdc" in out
    assert ".cursor/mcp.json" in out
    assert ".skills/development/SKILL.md" not in out      # 스킬은 규칙으로 변환됨
    overview = out[".cursor/rules/00-overview.mdc"].decode("utf-8")
    assert overview.startswith("---\n") and "alwaysApply: true" in overview
    assert ".cursor/rules/development.mdc" in overview     # 경로 참조 치환
    rule = out[".cursor/rules/development.mdc"].decode("utf-8")
    assert "alwaysApply: false" in rule and "description:" in rule


def test_secret_not_inline_in_configs(schema, catalog, answers):
    eff = apply_defaults(answers, schema)
    base = generate_files(TEMPLATE, eff, schema)
    servers, ev, ex = build_mcp(answers, catalog)
    claude = adapt_target("claude-code", base, servers, ev, ex)
    codex = adapt_target("codex", base, servers, ev, ex)
    cursor = adapt_target("cursor", base, servers, ev, ex)
    assert b"ghp_example_token_123" not in claude[".mcp.json"]
    assert b"ghp_example_token_123" not in codex[".codex/config.toml"]
    assert b"ghp_example_token_123" not in cursor[".cursor/mcp.json"]
    # 토큰은 .env로만
    assert b"ghp_example_token_123" in claude[".env"]


# ---------------------------------------------------------------- end-to-end
def test_triple_target_nests_under_folders(schema, catalog, answers):
    files = generate_bundle(TEMPLATE, answers, schema, catalog)
    assert "claude-code/CLAUDE.md" in files
    assert "codex/AGENTS.md" in files
    assert "cursor/.cursor/rules/00-overview.mdc" in files
    assert "claude-code/.mcp.json" in files
    assert "codex/.codex/config.toml" in files
    assert "cursor/.cursor/mcp.json" in files


def test_single_target_at_root(schema, catalog, answers):
    answers["target.tools"] = ["Claude Code"]
    files = generate_bundle(TEMPLATE, answers, schema, catalog)
    assert "CLAUDE.md" in files
    assert not any(k.startswith("claude-code/") for k in files)


def test_generate_zip_roundtrip(schema, catalog, answers):
    data = generate_zip(TEMPLATE, answers, schema, catalog=catalog, root_dir="payments-api")
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        assert "payments-api/claude-code/CLAUDE.md" in names
        assert "payments-api/codex/AGENTS.md" in names
