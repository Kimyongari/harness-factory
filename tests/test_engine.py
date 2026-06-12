import io
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from harness_maker.engine import (
    ValidationError,
    adapt_target,
    apply_defaults,
    build_git_hooks,
    build_hook_scripts,
    build_mcp,
    generate_bundle,
    generate_files,
    generate_zip,
    load_catalog,
    load_checks,
    load_schema,
    substitute_text,
    validate,
)

ROOT = Path(__file__).resolve().parents[1]
SURVEY = ROOT / "survey.ko.yaml"
SURVEY_EN = ROOT / "survey.en.yaml"
CATALOG = ROOT / "mcp_catalog.yaml"
CHECKS = ROOT / "checks_catalog.yaml"
TEMPLATE = ROOT / "template" / "ko"
TEMPLATE_EN = ROOT / "template" / "en"


@pytest.fixture
def schema():
    return load_schema(SURVEY)


@pytest.fixture
def catalog():
    return load_catalog(CATALOG)


@pytest.fixture
def checks():
    return load_checks(CHECKS)


@pytest.fixture
def answers():
    return json.loads((ROOT / "tests" / "sample_answers.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 스키마/검증
def test_required_minimized(schema):
    assert schema.required_keys <= {
        "target.tools",
        "project.name",
        "project.description",
        "project.language",
        "project.package_manager",
        "profile.role",
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
            "target.tools": ["Claude Code"],
            "project.name": "x",
            "project.description": "y",
            "project.language": "Python",
            "project.package_manager": "pip",
            "profile.role": "backend",
            "mcp.servers": ["github"],
            "mcp.tokens": {"GITHUB_PERSONAL_ACCESS_TOKEN": "t"},
        },
        schema,
    )


def test_defaults_applied_when_step_skipped(schema):
    raw = {
        "target.tools": ["Claude Code"],
        "project.name": "x",
        "project.description": "y",
        "project.language": "Python",
        "project.package_manager": "pip",
        "profile.role": "backend",
    }
    eff = apply_defaults(raw, schema)
    assert eff["docs.language"] == "한국어"
    assert eff["gh.default_branch"] == "main"
    assert ".env" in eff["dev.never_touch"]


# ---------------------------------------------------------------- 치환
def test_substitute_joins_lists(schema):
    out, _ = substitute_text(
        "{{FILL:dev.never_touch}}", {"dev.never_touch": [".env", "x/"]}, schema
    )
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


# ---------------------------------------------------------------- 훅 스크립트
def test_build_hook_scripts(checks, answers):
    out = build_hook_scripts(answers, checks)
    pre = out[".scripts/pre-commit.sh"].decode("utf-8")
    post = out[".scripts/post-commit.sh"].decode("utf-8")
    assert "ruff check ." in pre and "ruff format ." in pre
    assert "pytest -q" in post
    assert pre.startswith("#!/usr/bin/env bash")


def test_hook_scripts_in_bundle_and_executable(schema, catalog, checks, answers):
    answers["target.tools"] = ["Claude Code"]
    files = generate_bundle(TEMPLATE, answers, schema, catalog, checks)
    assert ".scripts/pre-commit.sh" in files
    assert ".scripts/post-commit.sh" in files
    # zip에서 .sh 실행권한(0o755) 부여 확인
    data = generate_zip(TEMPLATE, answers, schema, catalog=catalog, checks=checks, root_dir="h")
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        info = zf.getinfo("h/.scripts/pre-commit.sh")
        assert (info.external_attr >> 16) & 0o111  # 실행 비트


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


def test_claude_settings_hooks(schema, catalog, answers):
    eff = apply_defaults(answers, schema)
    base = generate_files(TEMPLATE, eff, schema)
    servers, ev, ex = build_mcp(answers, catalog)
    out = adapt_target("claude-code", base, servers, ev, ex)
    assert ".claude/settings.json" in out
    cfg = json.loads(out[".claude/settings.json"].decode("utf-8"))
    # PreToolUse(Bash) → guard-bash.sh (파괴적 명령 차단; Claude 런타임이 강제)
    pre = cfg["hooks"]["PreToolUse"][0]
    assert pre["matcher"] == "Bash"
    assert "guard-bash.sh" in pre["hooks"][0]["command"]
    # PostToolUse → pre-commit.sh, Stop → verify.sh
    pt = cfg["hooks"]["PostToolUse"][0]
    assert "Edit" in pt["matcher"] and "Write" in pt["matcher"]
    assert "pre-commit.sh" in pt["hooks"][0]["command"]
    stop = cfg["hooks"]["Stop"][0]
    assert "verify.sh" in stop["hooks"][0]["command"]


def test_guard_bash_in_bundle_with_never_touch(schema, catalog, checks, answers):
    """guard-bash.sh 는 zip 에 포함되어야 하고, 사용자의 never_touch 경로가 치환되어 있어야 한다."""
    files = generate_bundle(TEMPLATE, answers, schema, catalog, checks)
    # 단일 타깃 아닌 답변(샘플은 3개 도구) → 도구별 폴더 아래
    candidates = [k for k in files if k.endswith(".scripts/guard-bash.sh")]
    assert candidates, "guard-bash.sh missing from bundle"
    body = files[candidates[0]].decode("utf-8")
    assert "{{FILL:" not in body  # 치환 완료
    assert ".env" in body  # sample_answers 의 never_touch 항목
    # zip 안에서 실행 권한 부여되는지 확인
    data = generate_zip(TEMPLATE, answers, schema, catalog=catalog, checks=checks, root_dir="h")
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        info = next(i for i in zf.infolist() if i.filename.endswith(".scripts/guard-bash.sh"))
        assert (info.external_attr >> 16) & 0o111


def test_codex_sandbox_approval_always_present(schema, catalog, answers):
    eff = apply_defaults(answers, schema)
    base = generate_files(TEMPLATE, eff, schema)
    # MCP 서버 선택 안 했어도 안전 정책 + 결정론적 훅은 항상 포함되어야 한다.
    out_no_mcp = adapt_target("codex", base, [], [], [])
    out_with_mcp = adapt_target("codex", base, *build_mcp(answers, catalog))
    for out in (out_no_mcp, out_with_mcp):
        toml = out[".codex/config.toml"].decode("utf-8")
        assert 'sandbox_mode = "workspace-write"' in toml
        assert 'approval_policy = "on-request"' in toml
        # 결정론적 hooks — Claude 와 동일한 이벤트 스키마.
        assert "[[hooks.PreToolUse]]" in toml
        assert 'matcher = "Bash"' in toml
        assert "guard-bash.sh" in toml
        assert "[[hooks.Stop]]" in toml
        assert "verify.sh" in toml


def test_codex_adapter_layout(schema, catalog, answers):
    eff = apply_defaults(answers, schema)
    base = generate_files(TEMPLATE, eff, schema)
    servers, ev, ex = build_mcp(answers, catalog)
    out = adapt_target("codex", base, servers, ev, ex)
    assert "AGENTS.md" in out and "AGENT.md" not in out
    assert ".skills/development/SKILL.md" in out  # 스킬은 그대로
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
    assert ".skills/development/SKILL.md" not in out  # 스킬은 규칙으로 변환됨
    overview = out[".cursor/rules/00-overview.mdc"].decode("utf-8")
    assert overview.startswith("---\n") and "alwaysApply: true" in overview
    assert ".cursor/rules/development.mdc" in overview  # 경로 참조 치환
    rule = out[".cursor/rules/development.mdc"].decode("utf-8")
    assert "alwaysApply: false" in rule and "description:" in rule
    # development 규칙은 코드 파일 globs 로 자동 첨부(결정론적) — description 단독(LLM-judgment) 금지.
    assert "globs: **/*.py" in rule
    # web-research 는 파일 범위가 없어 description 기반 유지(globs 비어있음).
    web = out[".cursor/rules/web-research.mdc"].decode("utf-8")
    assert "globs: \n" in web or "globs:\n" in web


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


# ----------------------------------------- karpathy 원칙이 템플릿에 명시적으로 박혀있나
KARPATHY_MARKERS = {
    "ko": [
        ("template/ko/AGENT.md", "구현 전에 가정을 드러낸다"),
        ("template/ko/AGENT.md", "X 한다 → Y 로 검증"),
        ("template/ko/.skills/development/SKILL.md", "코드 짜기 전에 생각하기"),
        ("template/ko/.skills/development/SKILL.md", "목표 주도 실행"),
        ("template/ko/.skills/development/SKILL.md", "Read → Think → Plan → Edit → Verify"),
    ],
    "en": [
        ("template/en/AGENT.md", "Surface assumptions before implementing"),
        ("template/en/AGENT.md", 'Frame the task as "do X → verify Y"'),
        ("template/en/.skills/development/SKILL.md", "Think before coding"),
        ("template/en/.skills/development/SKILL.md", "Goal-driven execution"),
        ("template/en/.skills/development/SKILL.md", "Read -> Think -> Plan -> Edit -> Verify"),
    ],
}


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_karpathy_principles_present_in_template(lang):
    """Karpathy 4원칙 중 향후 회귀하기 쉬운 'Think Before Coding' / 'Goal-Driven' 이
    AGENT.md / development SKILL.md 에 박혀있는지 확인."""
    for rel, marker in KARPATHY_MARKERS[lang]:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert marker in text, f"{rel} 에 '{marker}' 없음 — karpathy 원칙 회귀"


# --------------------------------------------------- checks_catalog 사용자 설명
def test_every_check_has_bilingual_description(checks):
    """프런트에서 사용자가 '이 검사가 뭘 하는지' 알아볼 수 있도록 한 줄 설명이 있어야 한다."""
    missing = [
        c["id"]
        for c in checks
        if not (str(c.get("description", "")).strip() and str(c.get("description_en", "")).strip())
    ]
    assert not missing, f"description/description_en 누락: {missing}"


# ---------------------------------------------------------------- i18n (en)
def test_en_schema_keys_match_ko(schema):
    en = load_schema(SURVEY_EN)
    assert en.keys == schema.keys  # 키 셋이 ko/en 동일해야 한다
    assert en.required_keys == schema.required_keys


def test_en_template_no_leftover_no_drift(catalog):
    en_schema = load_schema(SURVEY_EN)
    answers = {
        "target.tools": ["Claude Code"],
        "project.name": "demo",
        "project.description": "d",
        "project.language": "Go",
        "project.package_manager": "go mod",
        "profile.role": "backend",
    }
    eff = apply_defaults(answers, en_schema)
    files = generate_files(TEMPLATE_EN, eff, en_schema)
    assert not [p for p, c in files.items() if b"{{FILL:" in c]
    # 영문 기본값이 적용됐는지
    claude = generate_bundle(TEMPLATE_EN, answers, en_schema, catalog)
    assert b"English" in claude["CLAUDE.md"] or b"Concise" not in claude["CLAUDE.md"]


# ---------------------------------------------- guard-bash.sh 가 실제로 deny 하나 (크로스툴)
def _render_guard(template_dir, schema, answers):
    """템플릿의 guard-bash.sh 를 치환해 실행 가능한 스크립트 텍스트로 만든다."""
    eff = apply_defaults(answers, schema)
    files = generate_files(template_dir, eff, schema)
    return files[".scripts/guard-bash.sh"].decode("utf-8")


def _run_guard(script_text, tmp_path, payload):
    p = tmp_path / "guard-bash.sh"
    p.write_text(script_text, encoding="utf-8")
    res = subprocess.run(
        ["bash", str(p)], input=payload, capture_output=True, text=True, timeout=15
    )
    return res.stdout


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash 필요")
@pytest.mark.parametrize(
    "payload,should_deny",
    [
        # 공백 없는(compact) JSON — Claude/Codex 가 단일행으로 직렬화하는 형태.
        ('{"tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/x"}}', True),
        # 공백 있는(spaced) JSON — docs 가 렌더하는 형태. 회귀 방지: 이게 silent-pass 였다.
        ('{"tool_name": "Bash", "tool_input": {"command": "rm -rf /tmp/x"}}', True),
        ('{"tool_name": "Bash", "tool_input": {"command": "git push --force origin main"}}', True),
        ('{"tool_name": "Bash", "tool_input": {"command": "git commit --no-verify -m x"}}', True),
        ('{"tool_name": "Bash", "tool_input": {"command": "echo y > .env"}}', True),
        # 무해한 명령은 조용히 통과(출력 없음).
        ('{"tool_name": "Bash", "tool_input": {"command": "ls -la"}}', False),
        ('{"tool_name": "Bash", "tool_input": {"command": "git push origin feature"}}', False),
    ],
)
@pytest.mark.parametrize("template", [TEMPLATE, TEMPLATE_EN])
def test_guard_bash_denies_regardless_of_json_whitespace(template, payload, should_deny, tmp_path):
    """guard-bash.sh 는 콜론 뒤 공백 유무와 무관하게 deny 해야 한다(Claude·Codex 공통).

    회귀: 예전엔 `"command":"`(공백 없음)만 매칭해 spaced JSON 을 전부 통과시켰다.
    """
    sch = load_schema(SURVEY if template == TEMPLATE else SURVEY_EN)
    answers = {
        "target.tools": ["Cursor"],
        "project.name": "x",
        "project.description": "y",
        "project.language": "Python",
        "project.package_manager": "pip",
        "profile.role": "backend",
        "dev.never_touch": [".env", "secrets/"],
        "gh.default_branch": "main",
    }
    out = _run_guard(_render_guard(template, sch, answers), tmp_path, payload)
    denied = '"permissionDecision":"deny"' in out
    assert denied is should_deny, f"payload={payload!r} → out={out!r}"


# ---------------------------------------------------- 도구 무관 git 훅 (core.hooksPath)
def test_build_git_hooks_protected_branch():
    out = build_git_hooks({"gh.default_branch": "release"})
    assert set(out) == {".githooks/pre-commit", ".githooks/pre-push"}
    pre_push = out[".githooks/pre-push"].decode("utf-8")
    assert 'PROTECTED="release"' in pre_push
    assert "merge-base --is-ancestor" in pre_push  # 강제 푸시 탐지
    pre_commit = out[".githooks/pre-commit"].decode("utf-8")
    assert "pre-commit.sh" in pre_commit and pre_commit.startswith("#!/usr/bin/env bash")


def test_git_hooks_in_every_target_and_executable(schema, catalog, checks, answers):
    """git 훅은 모든 타깃 산출물에 포함되고 zip 에서 실행권한이 있어야 한다."""
    files = generate_bundle(TEMPLATE, answers, schema, catalog, checks)
    for target in ("claude-code", "codex", "cursor"):
        assert f"{target}/.githooks/pre-commit" in files
        assert f"{target}/.githooks/pre-push" in files
    data = generate_zip(TEMPLATE, answers, schema, catalog=catalog, checks=checks, root_dir="h")
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            if "/.githooks/" in f"/{info.filename}":
                assert (info.external_attr >> 16) & 0o111, info.filename


def test_single_target_git_hooks_at_root(schema, catalog, answers):
    answers["target.tools"] = ["Claude Code"]
    files = generate_bundle(TEMPLATE, answers, schema, catalog)
    assert ".githooks/pre-commit" in files and ".githooks/pre-push" in files


# --------------------------------------------- 크로스툴 강제 문구가 산출물에 명시됐나
def test_codex_config_documents_cwd_and_compat(schema, catalog, answers):
    eff = apply_defaults(answers, schema)
    base = generate_files(TEMPLATE, eff, schema)
    out = adapt_target("codex", base, *build_mcp(answers, catalog))
    toml = out[".codex/config.toml"].decode("utf-8")
    assert "session cwd" in toml  # 상대경로 cwd 주의
    assert "guard-bash.sh 가 그대로 동작" in toml  # 스키마 호환(어댑터 불필요) 명시


def test_cursor_overview_states_advisory_and_git_hooks(schema, catalog, answers):
    files = generate_bundle(TEMPLATE, answers, schema, catalog)
    overview = files["cursor/.cursor/rules/00-overview.mdc"].decode("utf-8")
    assert "조언적" in overview  # Cursor 강제는 조언적임을 명시
    assert "core.hooksPath .githooks" in overview  # 도구 무관 강제 경로 안내
