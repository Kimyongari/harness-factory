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
    apply_skill_fills,
    build_git_hooks,
    build_hook_scripts,
    build_mcp,
    build_zip,
    generate_bundle,
    generate_files,
    generate_zip,
    load_catalog,
    load_checks,
    load_schema,
    model_tier,
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
def schema_for():
    """언어별 스키마 로더. ko/en 두 산출물을 같은 테스트로 검사할 때 쓴다."""

    def _load(lang: str):
        return load_schema(SURVEY if lang == "ko" else SURVEY_EN)

    return _load


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
    apply_skill_fills(eff, "ko")  # generate_bundle 이 하는 파생 필(라우팅 표) 재현
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
    apply_skill_fills(eff, "ko")
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
    # PostToolUse(*) → trace.sh (모든 도구 호출 궤적 기록)
    trace = next(h for h in cfg["hooks"]["PostToolUse"] if "trace.sh" in h["hooks"][0]["command"])
    assert trace["matcher"] == "*"
    stop = cfg["hooks"]["Stop"][0]
    assert "verify.sh" in stop["hooks"][0]["command"]
    # SessionStart → session-context.sh (압축/재개 시 상태 재주입)
    ss = cfg["hooks"]["SessionStart"][0]
    assert "compact" in ss["matcher"]
    assert "session-context.sh" in ss["hooks"][0]["command"]
    # PreCompact → precompact-note.sh
    assert "precompact-note.sh" in cfg["hooks"]["PreCompact"][0]["hooks"][0]["command"]


def test_claude_native_sandbox(schema, catalog):
    """settings.json 에 네이티브 OS 샌드박스가 켜지고 never_touch/.env 가 보호되어야 한다."""
    answers = {
        "target.tools": ["Claude Code"],
        "project.name": "demo",
        "project.description": "d",
        "project.language": "Python",
        "project.package_manager": "uv",
        "profile.role": "backend",
        "dev.never_touch": [".env", "secrets/"],
    }
    out = generate_bundle(TEMPLATE, answers, schema, catalog)
    cfg = json.loads(out[".claude/settings.json"].decode("utf-8"))
    sb = cfg["sandbox"]
    assert sb["enabled"] is True
    assert sb["failIfUnavailable"] is False  # 미지원 OS 는 폴백(하드 실패 아님)
    assert "secrets/" in sb["filesystem"]["denyWrite"]
    assert "secrets/" in sb["filesystem"]["denyRead"]
    # .env + never_touch 는 credentials 로도 읽기 차단(환경변수 unset 대비)
    cred_paths = {f["path"] for f in sb["credentials"]["files"]}
    assert ".env" in cred_paths and "secrets/" in cred_paths
    assert all(f["mode"] == "deny" for f in sb["credentials"]["files"])


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
        assert "[[hooks.PostToolUse]]" in toml
        assert "trace.sh" in toml
        assert "[[hooks.Stop]]" in toml
        assert "verify.sh" in toml
        # SessionStart / PreCompact 훅도 포함
        assert "[[hooks.SessionStart]]" in toml
        assert "session-context.sh" in toml
        assert "[[hooks.PreCompact]]" in toml
        assert "precompact-note.sh" in toml
        # Codex 는 훅을 처음 실행 전 /hooks 로 신뢰해야 발동한다 — 안내가 포함되어야 한다.
        assert "/hooks" in toml


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
    apply_skill_fills(eff, "ko")
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
    # Cursor 런타임 훅 — beforeShellExecution→guard-bash, afterFileEdit→pre-commit
    assert ".cursor/hooks.json" in out
    hooks = json.loads(out[".cursor/hooks.json"].decode("utf-8"))
    assert "guard-bash.sh" in hooks["hooks"]["beforeShellExecution"][0]["command"]
    assert "pre-commit.sh" in hooks["hooks"]["afterFileEdit"][0]["command"]


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
# 원칙은 **development 스킬 한 곳에만** 둔다. 이전에는 AGENT.md 에도 같은 내용을 적어
# 두 곳에서 반복했는데, 항상 로드되는 파일에 중복을 쌓는 것은 컨텍스트 예산을 두 번 쓰는 일이다.
# 이 가드의 목적은 "원칙이 하네스에서 사라지지 않았는지" 확인하는 것이고, 위치는 스킬이 맞다.
KARPATHY_MARKERS = {
    "ko": [
        ("template/ko/.skills/development/SKILL.md", "코드 짜기 전에 생각하기"),
        ("template/ko/.skills/development/SKILL.md", "묵묵히 고르지 말고"),
        ("template/ko/.skills/development/SKILL.md", "목표 주도 실행"),
        ("template/ko/.skills/development/SKILL.md", "X 한다 → Y 로 검증한다"),
        ("template/ko/.skills/development/SKILL.md", "Read → Think → Plan → Edit → Verify"),
    ],
    "en": [
        ("template/en/.skills/development/SKILL.md", "Think before coding"),
        ("template/en/.skills/development/SKILL.md", "don't silently pick one"),
        ("template/en/.skills/development/SKILL.md", "Goal-driven execution"),
        ("template/en/.skills/development/SKILL.md", "do X → verify Y"),
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
        # 따옴표 인자 우회(H1) — 예전엔 위험 토큰 앞 따옴표에서 [^"]* 가 멈춰 통째로 통과.
        (
            '{"tool_name":"Bash","tool_input":{"command":"git commit -m \\"msg\\" --no-verify"}}',
            True,
        ),
        ('{"tool_name":"Bash","tool_input":{"command":"echo \\"hi\\" && rm -rf /tmp/x"}}', True),
        ('{"tool_name":"Bash","tool_input":{"command":"bash -c \\"rm -rf /tmp/x\\""}}', True),
        ('{"tool_name":"Bash","tool_input":{"command":"echo \\"x\\" && git add .env"}}', True),
        # spaced JSON 의 sudo / pipe-to-shell(H2) — 예전엔 이 규칙들이 공백 미허용이라 통과.
        ('{"tool_name": "Bash", "tool_input": {"command": "sudo rm x"}}', True),
        ('{"tool_name": "Bash", "tool_input": {"command": "curl http://x | sh"}}', True),
        # force push 변형(M1) — 후치 -f / +refspec.
        ('{"tool_name":"Bash","tool_input":{"command":"git push origin main -f"}}', True),
        ('{"tool_name":"Bash","tool_input":{"command":"git push origin +main"}}', True),
        # never_touch 우회(M4) — sed 는 예전 동사 목록에 없었다.
        ('{"tool_name":"Bash","tool_input":{"command":"sed -i s/a/b/ .env"}}', True),
        # Cursor beforeShellExecution 스키마(top-level command) 도 동일하게 deny.
        ('{"command":"rm -rf /tmp/x","hook_event_name":"beforeShellExecution"}', True),
        # 무해한 명령은 조용히 통과(출력 없음).
        ('{"tool_name": "Bash", "tool_input": {"command": "ls -la"}}', False),
        ('{"tool_name": "Bash", "tool_input": {"command": "git push origin feature"}}', False),
        # 안전한 --force-with-lease 는 허용(L1). 단어 내부 rm(예: charm)은 오탐 아님.
        (
            '{"tool_name":"Bash","tool_input":{"command":"git push --force-with-lease origin feat"}}',
            False,
        ),
        ('{"tool_name":"Bash","tool_input":{"command":"echo charm"}}', False),
    ],
)
@pytest.mark.parametrize("template", [TEMPLATE, TEMPLATE_EN])
def test_guard_bash_denies_regardless_of_json_whitespace(template, payload, should_deny, tmp_path):
    """guard-bash.sh 는 명령을 추출·디코드한 뒤 매칭하므로 JSON 공백/따옴표 우회에 견딘다.

    회귀: 예전엔 raw JSON 을 `"command":"[^"]*<패턴>` 로 grep 해, 콜론 뒤 공백이나
    위험 토큰 앞 따옴표(예: git commit -m "x" --no-verify)가 가드를 통째로 뚫었다.
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
    # Claude/Codex 는 permissionDecision, Cursor 는 permission 형식으로 deny 한다.
    denied = '"permissionDecision":"deny"' in out or '"permission":"deny"' in out
    assert denied is should_deny, f"payload={payload!r} → out={out!r}"


# ----------------------------------------------- trace.sh 가 유효한 JSONL 을 남기나
@pytest.mark.skipif(shutil.which("bash") is None, reason="bash 필요")
@pytest.mark.parametrize(
    "payload,expect_tool,expect_cmd",
    [
        # compact / spaced JSON 모두 — guard-bash 와 같은 회귀 포인트.
        ('{"hook_event_name":"PostToolUse","tool_name":"Read","tool_input":{}}', "Read", None),
        (
            '{"hook_event_name": "PostToolUse", "tool_name": "Bash",'
            ' "tool_input": {"command": "ls -la"}}',
            "Bash",
            "ls -la",
        ),
        # 이스케이프된 따옴표가 있는 명령도 유효한 JSON 라인으로 남아야 한다.
        (
            '{"tool_name":"Bash","tool_input":{"command":"echo \\"hi\\" > out.txt"}}',
            "Bash",
            'echo "hi" > out.txt',
        ),
    ],
)
@pytest.mark.parametrize("template", [TEMPLATE, TEMPLATE_EN])
def test_trace_sh_appends_valid_jsonl(template, payload, expect_tool, expect_cmd, tmp_path):
    """trace.sh 는 훅 페이로드에서 도구명/명령을 뽑아 파싱 가능한 JSONL 로 append 한다."""
    script = (template / ".scripts" / "trace.sh").read_text(encoding="utf-8")
    p = tmp_path / "trace.sh"
    p.write_text(script, encoding="utf-8")
    res = subprocess.run(
        ["bash", str(p)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=15,
        cwd=tmp_path,
    )
    assert res.returncode == 0, res.stderr
    lines = (tmp_path / ".trace" / "tools.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["tool"] == expect_tool
    assert entry.get("command") == expect_cmd or (expect_cmd is None and "command" not in entry)
    assert entry["ts"]


def test_trace_sh_in_every_target_bundle(schema, catalog, checks, answers):
    """trace.sh 는 산출물에 포함된다(런타임 훅이 없는 Cursor 도 템플릿 공통 파일로 받는다)."""
    files = generate_bundle(TEMPLATE, answers, schema, catalog, checks)
    assert [k for k in files if k.endswith(".scripts/trace.sh")]


# ---------------------------------------------------- 도구 무관 git 훅 (core.hooksPath)
def test_build_git_hooks_protected_branch():
    """기본 전략(브랜치 작업)에서는 보호 브랜치로의 **모든** 푸시를 거부한다.

    강제 푸시만 막으면 "보호 브랜치" 가 절반만 참이다 — 일반 푸시로도 리뷰 없이 main 이 바뀐다.
    """
    out = build_git_hooks({"gh.default_branch": "release"})
    assert set(out) == {".githooks/pre-commit", ".githooks/pre-push"}
    pre_push = out[".githooks/pre-push"].decode("utf-8")
    assert 'PROTECTED="release"' in pre_push
    assert "보호 브랜치입니다" in pre_push  # 일반 푸시까지 거부
    pre_commit = out[".githooks/pre-commit"].decode("utf-8")
    assert "pre-commit.sh" in pre_commit and pre_commit.startswith("#!/usr/bin/env bash")


def test_pre_push_allows_direct_pushes_when_that_is_the_chosen_strategy():
    """설문에서 "기본 브랜치에 직접 작업" 을 골랐다면 일반 푸시를 막을 수 없다.

    그게 그 전략의 정의다. 대신 히스토리를 재작성하는 강제 푸시는 그 경우에도 막는다.
    """
    out = build_git_hooks(
        {"gh.default_branch": "main", "dev.branch_strategy": "기본 브랜치에 직접 작업"}
    )
    pre_push = out[".githooks/pre-push"].decode("utf-8")
    assert "merge-base --is-ancestor" in pre_push  # 강제 푸시만 탐지
    assert "보호 브랜치입니다" not in pre_push


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


# 항상 로드되는 파일의 크기 예산. Claude 5 세대 컨텍스트 엔지니어링의 핵심 주장은
# "가장 작은 고신호 토큰 집합"이고, 이 파일들은 **모든 요청에** 들어간다.
# 백과사전화(everything important = nothing followed)로 되돌아가는 것을 막는 가드다.
ALWAYS_LOADED = {
    "claude-code": "CLAUDE.md",
    "codex": "AGENTS.md",
    "cursor": ".cursor/rules/00-overview.mdc",
}
# UTF-8 **바이트** 기준. 문자수로 재면 한글 1자가 3바이트라 언어에 따라 예산이 3배 달라진다.
# 개편 전 AGENT.md 는 ko 6393 / en 5956 바이트였다.
ALWAYS_LOADED_BUDGET = 3200


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_always_loaded_files_stay_within_budget(schema_for, answers, lang):
    """항상 로드되는 파일이 예산을 넘지 않는가.

    넘겼다면 내용을 지우기 전에 먼저 물어라: 이건 에이전트가 파일을 보면 아는 사실인가?
    일반적인 좋은 습관인가? 그렇다면 빼고, 이 레포에서만 참인 것만 남긴다.
    상세는 스킬(`.skills/`)이나 참조 문서(`.docs/references/`)로 옮긴다 — 필요할 때만 로드된다.
    """
    files = generate_bundle(ROOT / "template" / lang, answers, schema_for(lang), [])
    for target, name in ALWAYS_LOADED.items():
        size = len(files[f"{target}/{name}"])
        assert size <= ALWAYS_LOADED_BUDGET, (
            f"{lang}/{target}/{name} 가 {size}바이트 — 예산 {ALWAYS_LOADED_BUDGET}바이트 초과"
        )


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_always_loaded_file_carries_repo_gotchas(schema_for, answers, lang):
    """항상 로드되는 파일은 '레포 고유의 함정'을 담아야 한다.

    파일시스템에서 읽을 수 있는 사실보다, 코드를 읽어도 알 수 없는 제약이 훨씬 높은 신호다.
    """
    files = generate_bundle(ROOT / "template" / lang, answers, schema_for(lang), [])
    for target, name in ALWAYS_LOADED.items():
        text = files[f"{target}/{name}"].decode("utf-8")
        assert "otcha" in text or "함정" in text, f"{lang}/{target}/{name} 에 gotchas 절이 없다"


def test_cursor_overview_states_runtime_hooks_and_git_backstop(schema, catalog, answers):
    files = generate_bundle(TEMPLATE, answers, schema, catalog)
    overview = files["cursor/.cursor/rules/00-overview.mdc"].decode("utf-8")
    # 항상 로드되는 규칙에는 **이 도구의** 강제 방식만 둔다.
    assert ".cursor/hooks.json" in overview
    # 다른 타깃 이야기가 섞이지 않아야 한다(컨텍스트 낭비 + 혼동).
    assert "sandbox_mode" not in overview, "Codex 설정 설명이 Cursor 규칙에 들어갔다"
    assert ".claude/agents/" not in overview, "Claude Code 설명이 Cursor 규칙에 들어갔다"
    # git 훅 백스톱은 클론당 1회 하는 사람 작업이라 참조 문서로 옮겼다 —
    # 사라지지는 않았는지 확인한다(항상 로드되는 파일에 둘 필요는 없다).
    ref = files["cursor/.docs/references/harness.md"].decode("utf-8")
    assert "core.hooksPath .githooks" in ref
    assert ".githooks/pre-push" in ref


# ------------------------------------------ 하드닝: 안전 기본값 / 권한 / 서브에이전트
def _single_claude_answers():
    return {
        "target.tools": ["Claude Code"],
        "project.name": "demo",
        "project.description": "d",
        "project.language": "Python",
        "project.package_manager": "uv",
        "profile.role": "backend",
        "dev.never_touch": [".env", "secrets/"],
        "hooks.pre_commit": ["ruff-lint"],
        "hooks.post_commit": ["pytest"],
    }


def test_gitignore_always_present(schema, catalog, checks):
    """MCP 토큰이 없어도 .gitignore 가 생성되고 .env + never_touch 가 들어가야 한다."""
    out = generate_bundle(TEMPLATE, _single_claude_answers(), schema, catalog, checks)
    assert ".gitignore" in out
    gi = out[".gitignore"].decode("utf-8")
    assert ".env" in gi
    assert "!.env.example" in gi  # 예시는 커밋되도록 예외
    assert "secrets/" in gi  # never_touch 반영
    assert ".trace/" in gi  # trace.sh 로그는 로컬 전용


def test_claude_permissions_in_settings(schema, catalog, checks):
    out = generate_bundle(TEMPLATE, _single_claude_answers(), schema, catalog, checks)
    cfg = json.loads(out[".claude/settings.json"].decode("utf-8"))
    perms = cfg["permissions"]
    assert "Read" in perms["allow"]
    # 선택한 검사 명령이 allow 에 들어간다(ruff-lint → "ruff check .")
    assert any("ruff check" in a for a in perms["allow"])
    # push 는 allow — 보호 브랜치·강제 푸시는 pre-push 훅과 guard-bash 가 결정론적으로
    # 거부하므로, ask 로 또 막으면 헤드리스에서 정당한 피처 브랜치 push 까지 멈춘다.
    assert "Bash(git push:*)" in perms["allow"]
    assert not any("git push" in a for a in perms["ask"])
    # 결정론적 가드가 없는 되돌리기 어려운 작업만 ask
    assert any("git merge" in a for a in perms["ask"])
    # 시크릿/보호 경로 읽기는 deny(컨텍스트 유입 방지)
    assert "Read(./.env)" in perms["deny"]
    assert any("secrets" in d for d in perms["deny"])


def test_default_bundle_ships_all_skill_packs(schema, catalog, checks):
    """스킬 팩 미답(기본값)이면 라이브러리 전체(7종)가 담기고 라우팅 표가 전부를 가리킨다."""
    out = generate_bundle(TEMPLATE, _single_claude_answers(), schema, catalog, checks)
    for s in (
        "development",
        "debugging",
        "code-review",
        "quick-tasks",
        "github-workflow",
        "doc-writing",
        "web-research",
    ):
        assert f".claude/skills/{s}/SKILL.md" in out, s
        assert f".claude/skills/{s}/SKILL.md".encode() in out["CLAUDE.md"], f"라우팅 표에 {s} 없음"


def test_skill_pack_selection_prunes_bundle(schema, catalog, checks):
    """선택한 팩의 스킬만 담긴다 — 라우팅 표·agent.yaml 목록도 함께 줄어든다."""
    ans = {
        **_single_claude_answers(),
        "dev.skill_packs": ["일상·경량 (토큰 절약)", "Git/GitHub 협업"],
    }
    out = generate_bundle(TEMPLATE, ans, schema, catalog, checks)
    assert ".claude/skills/quick-tasks/SKILL.md" in out
    assert ".claude/skills/github-workflow/SKILL.md" in out
    for absent in ("development", "debugging", "code-review", "doc-writing", "web-research"):
        assert f".claude/skills/{absent}/SKILL.md" not in out, absent
    claude_md = out["CLAUDE.md"].decode("utf-8")
    assert "quick-tasks" in claude_md and "web-research" not in claude_md
    agent_yaml = out[".agents/agent.yaml"].decode("utf-8")
    assert "quick-tasks" in agent_yaml and "development" not in agent_yaml


def test_skill_descriptions_are_routing_rules():
    """description 은 요약이 아니라 라우팅 규칙이다 — 언제 발동하는지가 담겨야 한다.

    스킬 발동 실패의 대부분은 본문이 아니라 description 실패다(상시 로드되는 유일한 부분).
    """
    for lang in ("ko", "en"):
        for skill_md in sorted((ROOT / "template" / lang / ".skills").glob("*/SKILL.md")):
            head = skill_md.read_text(encoding="utf-8").split("---")[1]
            desc = next(line for line in head.splitlines() if line.startswith("description:"))
            assert len(desc) > 100, f"{skill_md}: description 이 라우팅 규칙치고 너무 짧다"
            markers = ("사용한다", "트리거", "Use ", "use ", "Triggers")
            assert any(m in desc for m in markers), f"{skill_md}: 발동 조건이 없다"
    # 토큰 절약 스킬은 그 목적이 description 에 드러나야 한다
    qt = (ROOT / "template/ko/.skills/quick-tasks/SKILL.md").read_text(encoding="utf-8")
    assert "토큰" in qt.splitlines()[2]


def test_new_skills_become_cursor_rules_with_globs(schema, catalog, answers):
    """debugging·code-review 는 코드 globs 로 자동 첨부, quick-tasks 는 description 기반."""
    eff = apply_defaults(answers, schema)
    apply_skill_fills(eff, "ko")
    base = generate_files(TEMPLATE, eff, schema)
    out = adapt_target("cursor", base, [], [], [])
    dbg = out[".cursor/rules/debugging.mdc"].decode("utf-8")
    assert "globs: **/*.py" in dbg
    qt = out[".cursor/rules/quick-tasks.mdc"].decode("utf-8")
    assert "globs: \n" in qt and "description:" in qt


def test_model_tier_normalization():
    """티어 판정은 라벨 문안이 아니라 표식 어휘로 한다 — ko/en 라벨을 모두 수용."""
    assert model_tier({"target.model_tier": "프론티어 (Claude Opus, GPT-5 급)"}) == "frontier"
    assert model_tier({"target.model_tier": "Frontier (Claude Opus, GPT-5 class)"}) == "frontier"
    assert model_tier({"target.model_tier": "소형·경량 (Haiku, mini 급)"}) == "small"
    assert model_tier({"target.model_tier": "Small / lightweight (Haiku, mini class)"}) == "small"
    assert model_tier({"target.model_tier": "혼용 / 잘 모름"}) == "mixed"
    assert model_tier({}) == "mixed"


def test_small_tier_injects_deterministic_security_check(schema, catalog, checks):
    """소형/혼용 티어 + Python 이면 ruff 보안 검사(bandit 계열)가 pre-commit 에 주입된다.

    근거: 보안 함정은 지시문 문장으로는 소형 모델에서 막히지 않는다(evals 실측,
    skill-text Δ≈0 · fatal 다수). 산문 대신 결정론적 검사가 막아야 한다.
    """
    ans = {**_single_claude_answers(), "target.model_tier": "소형·경량 (Haiku, mini 급)"}
    out = generate_bundle(TEMPLATE, ans, schema, catalog, checks)
    pre = out[".scripts/pre-commit.sh"].decode("utf-8")
    assert "ruff check --select S ." in pre
    # 주입된 명령은 permissions allow 에도 함께 들어간다(실행이 막히지 않게).
    perms = json.loads(out[".claude/settings.json"].decode("utf-8"))["permissions"]
    assert any("--select S" in a for a in perms["allow"])


def test_frontier_tier_skips_security_check_injection(schema, catalog, checks):
    """프론티어 단독 사용이 확실하면 주입하지 않는다 — 훅 비용 절약(사용자 선택은 존중)."""
    ans = {**_single_claude_answers(), "target.model_tier": "프론티어 (Claude Opus, GPT-5 급)"}
    out = generate_bundle(TEMPLATE, ans, schema, catalog, checks)
    assert "ruff check --select S ." not in out[".scripts/pre-commit.sh"].decode("utf-8")
    # 명시적으로 고른 경우는 티어와 무관하게 유지된다.
    ans2 = {**ans, "hooks.pre_commit": ["ruff-lint", "ruff-security"]}
    out2 = generate_bundle(TEMPLATE, ans2, schema, catalog, checks)
    assert "ruff check --select S ." in out2[".scripts/pre-commit.sh"].decode("utf-8")


def test_hook_script_is_quiet_on_success_and_verbose_on_failure(tmp_path, checks, answers):
    """훅은 편집마다 돌므로 통과 출력은 무음이어야 한다(반복 토큰 비용). 실패만 상세."""
    out = build_hook_scripts({"hooks.pre_commit": ["ruff-lint"], "hooks.post_commit": []}, checks)
    script = tmp_path / "pre-commit.sh"
    script.write_bytes(out[".scripts/pre-commit.sh"])
    ok_dir = tmp_path / "ok"
    ok_dir.mkdir()
    (ok_dir / "good.py").write_text("x = 1\n", encoding="utf-8")
    ok = subprocess.run(["bash", str(script)], cwd=ok_dir, capture_output=True, text=True)
    assert ok.returncode == 0
    assert "ruff" not in ok.stdout, f"성공 시 명령 출력이 새어나온다: {ok.stdout!r}"
    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    (bad_dir / "bad.py").write_text("import os\n", encoding="utf-8")  # F401 미사용 import
    bad = subprocess.run(["bash", str(script)], cwd=bad_dir, capture_output=True, text=True)
    assert bad.returncode == 1
    assert "F401" in bad.stdout, "실패 시에는 원인 출력이 그대로 보여야 한다"


def test_pytest_check_passes_when_no_tests_collected(tmp_path, checks):
    """테스트가 아직 없는 프로젝트가 완료 게이트에 갇히면 안 된다.

    pytest 는 수집된 테스트가 없으면 exit 5 를 낸다. 그걸 실패로 세면 문서만 고친
    커밋이나 테스트를 아직 안 쓴 프로젝트에서 `verify.sh` 가 **영원히** 통과하지
    못한다. 실측에서 에이전트가 이 게이트를 넘으려고 요청받지 않은 테스트를 지어냈다
    (03·04 harness 조건에만 `tests/` 가 생겼고 턴 수가 두 배였다).
    """
    out = build_hook_scripts({"hooks.pre_commit": [], "hooks.post_commit": ["pytest"]}, checks)
    script = tmp_path / "post-commit.sh"
    script.write_bytes(out[".scripts/post-commit.sh"])

    empty = tmp_path / "no-tests"
    empty.mkdir()
    (empty / "README.md").write_text("문서만 있는 프로젝트\n", encoding="utf-8")
    res = subprocess.run(["bash", str(script)], cwd=empty, capture_output=True, text=True)
    assert res.returncode == 0, f"테스트 없음(exit 5)이 실패로 처리됐다: {res.stdout!r}"

    # 진짜 실패는 여전히 잡아야 한다 — 통과 코드 확장이 게이트를 무디게 만들면 안 된다.
    failing = tmp_path / "failing"
    failing.mkdir()
    (failing / "test_x.py").write_text("def test_x():\n    assert False\n", encoding="utf-8")
    res = subprocess.run(["bash", str(script)], cwd=failing, capture_output=True, text=True)
    assert res.returncode == 1, "실패하는 테스트가 통과로 처리됐다"


def test_claude_subagents_generated(schema, catalog, checks):
    out = generate_bundle(TEMPLATE, _single_claude_answers(), schema, catalog, checks)
    assert ".claude/agents/explorer.md" in out
    assert ".claude/agents/reviewer.md" in out
    assert b"name: explorer" in out[".claude/agents/explorer.md"]
    assert b"name: reviewer" in out[".claude/agents/reviewer.md"]
    # 읽기 전용 explorer 는 저비용 모델로 지정(메인 토큰 절약).
    assert b"model: haiku" in out[".claude/agents/explorer.md"]
    # Codex/Cursor 에는 서브에이전트 정의를 만들지 않는다(해당 개념 없음)
    base = generate_files(TEMPLATE, apply_defaults(_single_claude_answers(), schema), schema)
    cod = adapt_target("codex", base, [], [], [])
    cur = adapt_target("cursor", base, [], [], [])
    assert not [k for k in cod if k.startswith(".claude/agents/")]
    assert not [k for k in cur if k.startswith(".claude/agents/")]


def test_guard_bash_blocks_pipe_to_shell_and_escalation(schema, catalog, checks):
    """확장된 가드 패턴(파이프-투-셸·권한상승·never_touch 스테이징)이 번들에 들어간다."""
    out = generate_bundle(TEMPLATE, _single_claude_answers(), schema, catalog, checks)
    body = out[".scripts/guard-bash.sh"].decode("utf-8")
    assert "(ba)?sh" in body  # curl | sh / | bash
    assert "sudo" in body
    assert "777" in body
    assert "git[[:space:]]+(add|stage)" in body  # never_touch 스테이징 차단


@pytest.mark.parametrize("tdir", [TEMPLATE, TEMPLATE_EN])
def test_skill_frontmatter_valid(tdir):
    """생성될 스킬 frontmatter 가 Anthropic 규칙을 지키는지(회귀 방지):
    name kebab-case·예약어 금지, description 존재·1024자 이하·XML 꺾쇠 금지."""
    import re as _re

    import yaml as _yaml

    skills = sorted((tdir / ".skills").glob("*/SKILL.md"))
    assert skills, "스킬을 찾지 못함"
    for sk in skills:
        text = sk.read_text(encoding="utf-8")
        m = _re.match(r"^---\n(.*?)\n---\n", text, _re.S)
        assert m, f"{sk}: frontmatter 없음"
        meta = _yaml.safe_load(m.group(1)) or {}
        name = str(meta.get("name", ""))
        desc = str(meta.get("description", ""))
        assert _re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name), (
            f"{sk}: name kebab-case 아님: {name!r}"
        )
        assert "claude" not in name and "anthropic" not in name, f"{sk}: name 에 예약어"
        assert desc, f"{sk}: description 없음"
        assert len(desc) <= 1024, f"{sk}: description 1024자 초과"
        assert "<" not in desc and ">" not in desc, f"{sk}: description 에 XML 꺾쇠"


# ----------------------------------------------- 신규 스크립트: 번들 포함 + 실행권한
def test_new_scripts_in_bundle_and_executable(schema, catalog, checks, answers):
    """session-context / precompact / trace 스크립트가 산출물에 들어가고 zip 에서 실행권한이 있어야 한다."""
    files = generate_bundle(TEMPLATE, answers, schema, catalog, checks)
    for suffix in (
        ".scripts/session-context.sh",
        ".scripts/precompact-note.sh",
        ".scripts/trace.sh",
    ):
        assert [k for k in files if k.endswith(suffix)], f"{suffix} missing"
    data = generate_zip(TEMPLATE, answers, schema, catalog=catalog, checks=checks, root_dir="h")
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            if info.filename.endswith(".scripts/session-context.sh"):
                assert (info.external_attr >> 16) & 0o111, info.filename


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash 필요")
@pytest.mark.parametrize("template", [TEMPLATE, TEMPLATE_EN])
def test_session_context_prints_plan_pointer(template, tmp_path):
    """session-context.sh 는 실행되어 PLAN.md 포인터를 stdout 으로 낸다(컨텍스트 주입)."""
    script = (template / ".scripts" / "session-context.sh").read_text(encoding="utf-8")
    p = tmp_path / "session-context.sh"
    p.write_text(script, encoding="utf-8")
    (tmp_path / "PLAN.md").write_text("x", encoding="utf-8")
    res = subprocess.run(["bash", str(p)], capture_output=True, text=True, timeout=15, cwd=tmp_path)
    assert res.returncode == 0, res.stderr
    assert "PLAN.md" in res.stdout


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash 필요")
@pytest.mark.parametrize("template", [TEMPLATE, TEMPLATE_EN])
def test_precompact_note_runs(template, tmp_path):
    script = (template / ".scripts" / "precompact-note.sh").read_text(encoding="utf-8")
    p = tmp_path / "precompact-note.sh"
    p.write_text(script, encoding="utf-8")
    res = subprocess.run(["bash", str(p)], capture_output=True, text=True, timeout=15)
    assert res.returncode == 0
    assert "PLAN.md" in res.stdout


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash 필요")
@pytest.mark.parametrize("template", [TEMPLATE, TEMPLATE_EN])
def test_verify_breaks_stop_loop(template, tmp_path):
    """verify.sh 는 stop_hook_active=true 훅 입력을 받으면 검사 없이 exit 0 (루프 방지)."""
    script = (template / ".scripts" / "verify.sh").read_text(encoding="utf-8")
    p = tmp_path / "verify.sh"
    p.write_text(script, encoding="utf-8")
    res = subprocess.run(
        ["bash", str(p)],
        input='{"stop_hook_active": true}',
        capture_output=True,
        text=True,
        timeout=15,
        cwd=tmp_path,
    )
    assert res.returncode == 0


def test_web_research_skill_restricts_tools():
    """web-research 스킬은 allowed-tools 로 도구를 제한한다(ko/en 템플릿)."""
    for tdir in (TEMPLATE, TEMPLATE_EN):
        text = (tdir / ".skills" / "web-research" / "SKILL.md").read_text(encoding="utf-8")
        assert "allowed-tools:" in text
        assert "WebSearch" in text and "WebFetch" in text


# ----------------------------------------------------------- Zip Slip 방어 (build_zip)
@pytest.mark.parametrize("bad_key", ["../../evil.sh", "/etc/abs", "a/../../b", "..\\..\\win"])
def test_build_zip_rejects_path_traversal(bad_key):
    """/api/zip 는 클라이언트가 준 키를 담으므로, '..'/절대경로는 거부해야 한다(Zip Slip)."""
    with pytest.raises(ValidationError):
        build_zip({bad_key: b"x"}, root_dir="harness")


def test_build_zip_accepts_normal_keys():
    data = build_zip({"CLAUDE.md": b"x", ".scripts/verify.sh": b"y"}, root_dir="harness")
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert "harness/CLAUDE.md" in zf.namelist()
