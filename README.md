# Harness Factory

**Answer a few questions → download a production-ready agent harness for Claude Code, Codex, or Cursor — with deterministic guardrails wired in.**

![Harness Factory demo](docs/demo.gif)

Harness engineering is the highest-ROI lever for coding agents — but writing a good `CLAUDE.md`, wiring skills, picking MCP servers, and setting safe guardrails by hand is tedious and easy to get wrong. Harness Factory turns that setup into a 4-step survey and hands you a drop-in bundle.

[![CI](https://github.com/Kimyongari/harness-factory/actions/workflows/ci.yml/badge.svg)](https://github.com/Kimyongari/harness-factory/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Targets](https://img.shields.io/badge/targets-Claude%20Code%20%7C%20Codex%20%7C%20Cursor-7c3aed.svg)](#-supported-tools)

> Available in **English and Korean** — toggle in the top-right of the wizard. 한국어 안내는 아래 [한국어](#-한국어) 섹션을 보세요.

---

## Why

> "Check the harness before changing the model — it's usually the best ROI." — the lesson teams keep relearning in 2026.

A model is only as good as the environment around it. Harness Factory bakes in the hard-won best practices so you don't have to:

- **Context hygiene** — a thin router file instead of a 1,000-line encyclopedia (avoids "everything important = nothing followed").
- **Karpathy-style behavioral rules baked into skills** — *Think before coding*, *simplicity first*, *surgical changes*, *goal-driven execution*. Inspired by [andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills); rephrased and wired in as the default skill bodies.
- **Mechanical enforcement (runtime, not prompt)** — destructive commands and protected paths are blocked by hooks the runtime fires; the LLM cannot opt out. See [Deterministic enforcement](#deterministic-enforcement) below.
- **Selective tools** — pick only the MCP servers you need (connecting all of them rots the context window).
- **Secrets stay safe** — tokens go to `.env` only; config files reference `${VARS}`, never inline.

## Deterministic enforcement

Three tools, one enforcement story — the runtime (not a prompt) fires every script below:

| Event | Claude Code | Codex | Cursor |
|---|---|---|---|
| Before any `Bash` | `PreToolUse` → `.scripts/guard-bash.sh` | `[[hooks.PreToolUse]]` matcher `Bash` → same script | n/a (relies on rules) |
| After `Edit` / `Write` | `PostToolUse` → `.scripts/pre-commit.sh` | n/a | n/a |
| Before "done" | `Stop` → `.scripts/verify.sh` | `[[hooks.Stop]]` → same script | n/a |
| Always loaded | `CLAUDE.md` (root) | `AGENTS.md` (root) | `.cursor/rules/00-overview.mdc` (`alwaysApply: true`) |
| Auto-attach by file type | n/a | n/a | `.cursor/rules/development.mdc`, `doc-writing.mdc` (`globs`) |
| Sandbox / approval | n/a | `sandbox_mode = "workspace-write"` + `approval_policy = "on-request"` | n/a |

`guard-bash.sh` blocks `rm -rf`, force pushes, `--no-verify`, and any write to your survey's `dev.never_touch` paths *before the call happens*. `verify.sh` runs the lint/test/boundary checks you picked before any "done" report. Both are plain bash — extend by editing the files; no plugin or daemon to install.

References: [Claude Code hooks](https://code.claude.com/docs/en/hooks), [Codex hooks](https://developers.openai.com/codex/hooks), [Cursor rules](https://cursor.com/docs/context/rules).

## What you get

A 4-step survey produces a harness covering **4 domains** — development, documentation, web research, and GitHub workflow — adapted to the tool you choose.

```
your-project/
├── CLAUDE.md / AGENTS.md / .cursor/rules/    # tool-specific instructions (Karpathy-style rules baked in)
├── .claude/skills/ · .skills/ · .cursor/rules/   # the 4 domain skill-sets / rules
├── .docs/                                    # hierarchical context (design, specs, plans, references)
├── .scripts/
│   ├── verify.sh           # the "before done" gate — boundaries → pre-commit → post-commit
│   ├── pre-commit.sh       # fast checks you picked (lint, format, typecheck)
│   ├── post-commit.sh      # heavier checks you picked (tests)
│   ├── check-boundaries.sh # layer-direction enforcement
│   └── guard-bash.sh       # PreToolUse: blocks rm -rf, force push, --no-verify, never_touch writes
├── .claude/settings.json   # hooks wiring (PreToolUse / PostToolUse / Stop) — Claude Code only
├── .codex/config.toml      # sandbox + approval + the same hooks — Codex only
├── .mcp.json / .cursor/mcp.json   # selected MCP servers per tool
└── .env(.example) + .gitignore   # your tokens, never committed
```

Pick more than one tool and each output nests under `claude-code/`, `codex/`, `cursor/`.

## 🚀 Quickstart

```bash
git clone https://github.com/Kimyongari/harness-factory.git
cd harness-factory

python -m venv .venv && source .venv/bin/activate
pip install -e .

harness-factory          # starts the web app at http://127.0.0.1:8000
```

Open the browser, pick **English or Korean** (top-right toggle), walk through the 4 steps, and download your `.zip`. Unzip it into your project root and you're done.

### 🐳 Or run with Docker

```bash
docker build -t harness-factory .
docker run --rm -p 8000:8000 harness-factory
# open http://127.0.0.1:8000
```

### CLI

Generate from a JSON answer file (`--lang ko|en`):

```bash
python -m harness_maker.engine --lang en --answers tests/sample_answers.json --out harness.zip
```

## 🧩 Supported tools

| | Claude Code | Codex | Cursor |
|---|---|---|---|
| Instructions | `CLAUDE.md` | `AGENTS.md` | `.cursor/rules/00-overview.mdc` (always) |
| Skills / Rules | `.claude/skills/*/SKILL.md` | `.skills/*` (referenced from `AGENTS.md`) | `.cursor/rules/*.mdc` (globs / agent-requested) |
| MCP config | `.mcp.json` | `.codex/config.toml` `[mcp_servers.X]` | `.cursor/mcp.json` |
| Secrets | `.env` (`${VAR}` refs) | `.env` (`env_vars` refs) | `.env` (`${VAR}` refs) |
| Deterministic hooks | `.claude/settings.json` (`PreToolUse` / `PostToolUse` / `Stop`) | `.codex/config.toml` (`[[hooks.PreToolUse]]` / `[[hooks.Stop]]`) | `alwaysApply` / `globs` rules |

Pick one or several — choosing multiple nests each under its own folder (`claude-code/`, `codex/`, `cursor/`).

## 📋 The survey (4 steps)

1. **Project** — name, language, framework, package manager (dropdowns; type your own if it's not listed).
2. **Dev conventions** *(skippable → safe defaults)* — install/run commands, **per-check picks for pre-commit and post-commit** (each option has a one-line description so you know what it does), never-touch paths, layer boundaries, commit style.
3. **Documentation** *(skippable → defaults)* — language, tone, format.
4. **Integrations & auth** *(skippable)* — pick MCP servers, enter only the tokens they need.

Only **5 fields are required**; everything else has a sensible default, so juniors can ship a good harness in under a minute.

> **Wizard self-explains the bundle.** Step 2 includes an inline panel describing what every `.scripts/*.sh` does and which runtime event fires it — no need to grep the zip to understand the layout.

## 🔌 MCP catalog

Curated for everyday development. Pick what you need:

`GitHub` · `Filesystem` · `Brave Search` · `Fetch` · `Notion` · `Slack` · `Sentry` · `PostgreSQL` · `Sequential Thinking` · `Playwright`

Token-based servers reveal their auth fields only when selected. Your tokens are written to `.env` (git-ignored) and referenced from config — never hard-coded.

## 🛠 How it works

```
survey.{ko,en}.yaml ─┐
mcp_catalog.yaml ────┤
checks_catalog.yaml ─┤→ engine: validate → defaults → substitute {{FILL}} → per-tool adapter → .zip
template/{ko,en}/ ───┘
```

- `template/` is the **framework-neutral** harness, full of `{{FILL:key}}` placeholders.
- `survey.yaml` is the single source of truth for what users fill in.
- `checks_catalog.yaml` lists every check preset (id, command, kind, **bilingual description**) — the wizard renders these as a multi-select; the engine inlines the chosen commands into `pre-commit.sh` / `post-commit.sh`.
- Adapters translate the neutral bundle into each tool's native layout — and wire the deterministic hooks for Claude / Codex.

## 📂 Project structure

```
harness-factory/
├── survey.ko.yaml / survey.en.yaml   # 4-step survey schema (per language)
├── mcp_catalog.yaml         # curated MCP servers (bilingual descriptions)
├── checks_catalog.yaml      # 17 lint/format/typecheck/test/security check presets
├── template/ko/  ·  template/en/     # the neutral harness (filled + zipped)
├── src/harness_maker/
│   ├── engine.py            # validate · default · substitute · adapt · zip
│   ├── app.py               # FastAPI: /api/survey, /api/generate, /api/preview
│   └── static/index.html    # 4-step wizard UI (KO/EN toggle, in-line preview)
├── Dockerfile
└── tests/                   # pytest suite (25 tests, incl. regression guards)
```

## 🧪 Development

```bash
pip install -e ".[dev]"
pre-commit install                 # lint/format hooks on commit
pre-commit install --hook-type pre-push   # run tests before push
pytest -q
```

Code quality is enforced by **pre-commit hooks** (ruff lint + format, plus YAML/JSON/TOML
checks, large-file/merge-conflict/private-key guards) and a **GitHub Actions CI** that runs
`ruff check`, `ruff format --check`, and `pytest` on every push and PR.

## 🗺 Roadmap

- [x] English & Korean survey UI + generated docs (i18n)
- [x] Docker packaging
- [x] Deterministic runtime hooks (Claude Code + Codex)
- [x] Cursor `globs`-based auto-attach for code/doc skills (no LLM-judgment)
- [x] Pre-download bundle preview (left tree + right viewer with Markdown render)
- [x] Per-check descriptions in the wizard
- [ ] More targets (Gemini CLI, Windsurf, Aider)
- [ ] Branching survey (questions adapt to earlier answers)
- [ ] Shareable harness presets

## 🤝 Contributing

Issues and PRs welcome — new MCP servers, new target adapters, more `checks_catalog` entries, and better default rules are especially appreciated. Adding a target is just one more adapter in `engine.py`.

## 📄 License

MIT — see [LICENSE](LICENSE).

---

## 🇰🇷 한국어

**설문 몇 개에 답하면 Claude Code · Codex · Cursor용 에이전트 하네스를, 결정론적 가드레일까지 박힌 상태로 zip으로 받습니다.**

좋은 하네스(=에이전트를 감싸는 지침·스킬·MCP·가드레일)는 모델 교체보다 ROI가 높지만, 직접 만들기는 번거롭습니다. Harness Factory는 그 셋업을 4단계 설문으로 바꿔 바로 쓸 수 있는 번들을 만들어 줍니다.

### 빠른 시작
```bash
git clone https://github.com/Kimyongari/harness-factory.git
cd harness-factory
python -m venv .venv && source .venv/bin/activate
pip install -e .
harness-factory        # http://127.0.0.1:8000
```
또는 Docker로:
```bash
docker build -t harness-factory . && docker run --rm -p 8000:8000 harness-factory
```
브라우저에서 언어(한국어/EN)를 고르고 4단계를 진행한 뒤 zip을 받아, 프로젝트 루트에 풀면 끝입니다.

### 핵심 특징

- **4개 도메인 스킬**: 개발 · 문서작업 · 웹검색 · 깃허브 — karpathy 4원칙("생각하고 코드 짜기 / 단순성 / 외과적 변경 / 목표 주도 실행")이 기본값으로 박혀 있습니다.
- **기계적 강제 (프롬프트 아님, 런타임)**:
  - `Bash` 호출 직전 → `.scripts/guard-bash.sh` 가 `rm -rf` / force push / `--no-verify` / `never_touch` 경로 쓰기를 차단 (Claude Code `PreToolUse`, Codex `[[hooks.PreToolUse]]`)
  - 파일 편집 직후 → `.scripts/pre-commit.sh` 자동 실행 (Claude Code `PostToolUse`)
  - "완료" 보고 직전 → `.scripts/verify.sh` 자동 실행 (Claude `Stop`, Codex `[[hooks.Stop]]`)
  - Cursor 스킬 규칙은 코드/문서 파일 `globs` 로 자동 첨부 — LLM 판단 X
- **검사 프리셋 17종**, 각각 한 줄 설명과 함께 위저드에서 선택. ruff / mypy / pytest / ESLint / tsc / go vet / cargo clippy / gitleaks 등.
- **필수 항목 5개**, 나머지는 기본값 — 주니어도 1분 안에 좋은 하네스 생성.
- **도구별 자동 변환**: Claude Code / Codex / Cursor (복수 선택 가능, 도구별 폴더로 분리).
- **토큰 안전**: `.env` 에만 저장, 설정 파일엔 `${VAR}` 참조, `.gitignore` 자동 포함.

### 4단계 설문

1. **프로젝트** — 이름·언어·프레임워크·패키지매니저
2. **개발 컨벤션** *(건너뛰기 가능)* — 명령, **pre/post-commit 검사 선택**(각 항목에 한 줄 설명), never_touch 경로, 레이어 경계, 커밋 스타일
3. **문서** *(건너뛰기 가능)* — 언어, 톤, 포맷
4. **연동 & 인증** *(건너뛰기 가능)* — MCP 서버 선택과 필요한 토큰만 입력

> Step 2 상단에 `.scripts/*.sh` 파일들이 각각 언제/무엇을 하는지 한 눈에 보여주는 패널이 있습니다. zip 을 받기 전에 무엇이 들어가는지 미리 압니다.

자세한 deterministic enforcement 표는 위 [영문 섹션](#deterministic-enforcement) 참고.
