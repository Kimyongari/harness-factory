# Harness Factory

**Answer a few questions → download a production-ready agent harness for Claude Code, Codex, or Cursor — with deterministic guardrails wired in.**

![Harness Factory demo](docs/demo.gif)

Harness engineering is the highest-ROI lever for coding agents — but writing a good `CLAUDE.md`, wiring skills, picking MCP servers, and setting safe guardrails by hand is tedious and easy to get wrong. Harness Factory turns that setup into a 4-step survey and hands you a drop-in bundle.

[![CI](https://github.com/Kimyongari/harness-factory/actions/workflows/ci.yml/badge.svg)](https://github.com/Kimyongari/harness-factory/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Targets](https://img.shields.io/badge/targets-Claude%20Code%20%7C%20Codex%20%7C%20Cursor-7c3aed.svg)](#-supported-tools)

> Available in **English and Korean** — toggle in the top-right of the wizard. 한국어 안내는 아래 [한국어](#-한국어) 섹션을 보세요.

> 🌐 **Try it live — no install:** **[Open the hosted Harness Factory →](http://134.185.104.194:8000)**
> A hosted instance is running on Oracle Cloud free tier. Just open it, answer the 4-step survey, and download your harness `.zip`.

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
| Before any `Bash` | `PreToolUse` → `guard-bash.sh` | `[[hooks.PreToolUse]]` (`Bash`) → same script | via git hooks ↓ |
| After `Edit` / `Write` | `PostToolUse` → `pre-commit.sh` | — | — |
| Before "done" | `Stop` → `verify.sh` | `[[hooks.Stop]]` → same script | — |
| On commit / push *(tool-agnostic)* | `.githooks/pre-commit` + `pre-push` | same | same |
| Always loaded | `CLAUDE.md` | `AGENTS.md` | `.cursor/rules/00-overview.mdc` (`alwaysApply`) |
| Auto-attach by file type | — | — | `.cursor/rules/*.mdc` (`globs`) |
| Least-privilege permissions | `settings.json` `allow`/`ask`/`deny` | — | — |
| Sandbox / approval | — | `sandbox_mode=workspace-write` + `approval_policy=on-request` | — |

`guard-bash.sh` blocks — *before the command runs* — `rm -rf`, force-push, `--no-verify`, pipe-to-shell (`curl … | sh`), privilege escalation (`sudo`, `chmod 777`), and any write **or staging** of your `dev.never_touch` paths (so secrets can't be committed). It denies regardless of how the runtime serializes its JSON. `verify.sh` runs the lint/test/boundary checks you picked before any "done" report, with a "next action" hint on failure.

Cursor has no runtime hooks, so its rules are advisory — but the bundle also ships **tool-agnostic git hooks** (`.githooks/`, enabled with `git config core.hooksPath .githooks`), so the same checks fire on commit/push no matter the tool. Everything is plain bash — extend by editing the files; no plugin or daemon to install.

References: [Claude Code hooks](https://code.claude.com/docs/en/hooks), [Codex hooks](https://developers.openai.com/codex/hooks), [Cursor rules](https://cursor.com/docs/context/rules).

## What you get

A 4-step survey produces a harness covering **4 domains** — development, documentation, web research, and GitHub workflow — adapted to the tool you choose.

```
your-project/
├── CLAUDE.md / AGENTS.md / .cursor/rules/    # tool-specific instructions (Karpathy-style rules baked in)
├── .claude/skills/ · .skills/ · .cursor/rules/   # the 4 domain skill-sets / rules
├── .claude/agents/         # explorer + reviewer subagents (Claude Code)
├── .docs/                  # hierarchical context (design, specs, plans, references)
├── .scripts/
│   ├── verify.sh           # the "before done" gate — boundaries → pre-commit → post-commit
│   ├── pre-commit.sh       # fast checks you picked (lint, format, typecheck)
│   ├── post-commit.sh      # heavier checks you picked (tests)
│   ├── check-boundaries.sh # layer-direction enforcement
│   └── guard-bash.sh       # PreToolUse guard: rm -rf, force push, pipe-to-shell, sudo/chmod 777, never_touch
├── .githooks/              # tool-agnostic pre-commit + pre-push (git config core.hooksPath .githooks)
├── .claude/settings.json   # hooks wiring + least-privilege permissions (allow/ask/deny) — Claude Code
├── .codex/config.toml      # sandbox + approval + the same hooks — Codex
├── .mcp.json / .cursor/mcp.json   # selected MCP servers per tool
└── .env(.example) + .gitignore   # tokens stay in .env; .gitignore is always included
```

Pick more than one tool and each output nests under `claude-code/`, `codex/`, `cursor/`.

## 📦 What's inside the harness (and why each part helps)

Every bundle is built on one idea: **steer the agent with structure, and enforce the must-haves with code — not hope.** In plain terms, here's what you get and why it matters.

- **A thin instruction file, not a wall of text** (`CLAUDE.md` / `AGENTS.md` / `.cursor/rules`). Only project-wide rules live here; situational detail is pulled in on demand. Bloated instruction files make agents *ignore* your rules — this keeps the always-loaded part small on purpose.
- **4 ready-made skills** — *development, doc-writing, web-research, github-workflow*. Each is a focused playbook the agent loads only when relevant (progressive disclosure), with Karpathy-style habits baked in: think before coding, keep it simple, make surgical changes, work goal-first.
- **Guardrails the agent can't talk its way past** (`guard-bash.sh` + runtime hooks). Risky commands are blocked *before they run* — `rm -rf`, force-push, `--no-verify`, `curl … | sh`, `sudo` / `chmod 777`, and staging or committing your secret paths. Prompt rules are advice; these are mechanical and fire every time.
- **A "before done" gate** (`verify.sh`). The agent can't claim success until your lint / format / test / boundary checks actually pass — and on failure it gets a concrete "next action," not just red output.
- **Least-privilege permissions** (Claude `settings.json`). Reads and the checks you picked are auto-allowed; `push` / `merge` ask first; reading `.env` and secret paths is denied — so secrets never slip into context.
- **Two helper subagents** (`.claude/agents/explorer`, `reviewer`). One explores the codebase read-only; the other reviews finished work with a fresh context. They keep the main conversation clean and add an independent second pair of eyes.
- **Secrets stay out of git** — tokens live in `.env` only (config files reference `${VARS}`), and a `.gitignore` covering `.env` plus your never-touch paths is always shipped.
- **The same guards everywhere** — they run on Claude Code (native hooks), Codex (`config.toml` hooks), and Cursor (via tool-agnostic git hooks, since Cursor rules are advisory only).

> New to harnesses? Generate one, unzip it, and skim `CLAUDE.md` — it routes you to everything else. The agent does the same.

## 🚀 Quickstart

> **Don't want to install anything?** A live instance is hosted — **[open Harness Factory](http://134.185.104.194:8000)** and skip straight to the survey.

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
| Deterministic hooks | `.claude/settings.json` (`PreToolUse` / `PostToolUse` / `Stop`) | `.codex/config.toml` (`[[hooks.PreToolUse]]` / `[[hooks.Stop]]`) | `.githooks/` (commit/push) + advisory rules |
| Permissions | `settings.json` `allow`/`ask`/`deny` | sandbox + approval policy | — |
| Subagents | `.claude/agents/explorer`, `reviewer` | — | — |

Pick one or several — choosing multiple nests each under its own folder (`claude-code/`, `codex/`, `cursor/`). Every tool also gets the tool-agnostic `.githooks/` so enforcement survives even where runtime hooks don't exist.

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
- Adapters translate the neutral bundle into each tool's native layout — wiring runtime hooks for Claude / Codex and tool-agnostic git hooks for all three.
- `evals/` holds golden tasks (fix a failing test, fix a lint error) so the *generated* harness can be exercised against a real agent, not just unit-tested.

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
├── evals/                   # golden tasks to exercise a generated harness with a real agent
├── Dockerfile
└── tests/                   # pytest suite (69 tests, incl. regression guards)
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
- [x] Tool-agnostic git hooks so enforcement reaches Cursor too
- [x] Least-privilege permissions + explorer/reviewer subagents (Claude Code)
- [x] Expanded `guard-bash` (pipe-to-shell, privilege escalation, secret staging)
- [x] Eval harness — golden tasks that run a generated harness against a real agent
- [ ] More targets (Gemini CLI, Windsurf, Aider)
- [ ] Branching survey (questions adapt to earlier answers)
- [ ] Prompt-injection defenses for untrusted tool/web content
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

> 🌐 **설치 없이 바로 써보기:** **[Harness Factory 열기 →](http://134.185.104.194:8000)** — Oracle Cloud 무료 티어에 올려둔 라이브 인스턴스입니다. 접속해서 4단계 설문에 답하고 하네스 zip을 받으면 됩니다.

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

### 생성되는 하네스의 특징 (쉽게)

핵심 철학은 하나입니다 — **에이전트를 구조로 유도하고, 꼭 지켜야 할 것은 "프롬프트"가 아니라 "코드"로 강제한다.** 받는 번들에는 이게 들어 있고, 각각 왜 도움이 되는지는 이렇습니다.

- **얇은 지침 파일** (`CLAUDE.md` / `AGENTS.md` / `.cursor/rules`): 프로젝트 전체에 적용되는 규칙만 두고, 나머지는 필요할 때 불러옵니다. 지침이 비대하면 에이전트가 오히려 규칙을 *무시*하기 때문에, 항상 로드되는 부분을 의도적으로 작게 유지합니다.
- **바로 쓰는 4개 스킬**: 개발 · 문서작업 · 웹검색 · 깃허브. 관련될 때만 로드되는 집중 플레이북이고(점진적 공개), karpathy 4원칙(생각하고 코딩 / 단순성 / 외과적 변경 / 목표 주도)이 기본으로 박혀 있습니다.
- **말로 못 빠져나가는 가드** (`guard-bash.sh` + 런타임 훅): 위험 명령을 *실행 전에* 차단 — `rm -rf`, force push, `--no-verify`, 파이프-투-셸(`curl … | sh`), 권한 상승(`sudo`/`chmod 777`), 그리고 시크릿(never_touch) 경로의 쓰기·**스테이징**. 프롬프트 규칙은 권고지만 이건 매번 기계적으로 동작합니다.
- **"완료" 직전 게이트** (`verify.sh`): 고른 린트·포맷·테스트·경계 검사가 실제로 통과해야 "완료"라고 말할 수 있고, 실패 시 빨간 출력이 아니라 "다음 행동"을 알려줍니다.
- **최소 권한** (Claude `settings.json`): 읽기와 고른 검사는 자동 허용, `push`/`merge` 는 확인, `.env`·시크릿 경로 읽기는 거부 — 시크릿이 컨텍스트로 새지 않습니다.
- **도우미 서브에이전트 2종** (`.claude/agents/explorer`, `reviewer`): 하나는 읽기 전용 탐색, 하나는 끝난 작업을 신선한 컨텍스트로 리뷰. 메인 대화를 깨끗하게 유지하고 독립 검증을 더합니다.
- **시크릿은 git 밖**: 토큰은 `.env` 에만(설정은 `${VAR}` 참조), `.env`+never_touch 를 담은 `.gitignore` 가 항상 포함됩니다.
- **도구가 달라도 같은 강제**: Claude Code(네이티브 훅)·Codex(`config.toml` 훅)·Cursor(규칙은 권고뿐이라 **도구 무관 git 훅** `.githooks/` 로 보강)에서 동일하게 동작합니다.

### 한눈 요약

- **검사 프리셋 17종**(ruff / mypy / pytest / ESLint / tsc / go vet / cargo clippy / gitleaks 등) — 각 항목에 한 줄 설명, 위저드에서 선택.
- **필수 항목 5개**, 나머지는 기본값 — 주니어도 1분 안에 좋은 하네스 생성.
- **3개 도구 자동 변환** — 복수 선택 시 도구별 폴더로 분리.

### 4단계 설문

1. **프로젝트** — 이름·언어·프레임워크·패키지매니저
2. **개발 컨벤션** *(건너뛰기 가능)* — 명령, **pre/post-commit 검사 선택**(각 항목에 한 줄 설명), never_touch 경로, 레이어 경계, 커밋 스타일
3. **문서** *(건너뛰기 가능)* — 언어, 톤, 포맷
4. **연동 & 인증** *(건너뛰기 가능)* — MCP 서버 선택과 필요한 토큰만 입력

> Step 2 상단에 `.scripts/*.sh` 파일들이 각각 언제/무엇을 하는지 한 눈에 보여주는 패널이 있습니다. zip 을 받기 전에 무엇이 들어가는지 미리 압니다.

자세한 deterministic enforcement 표는 위 [영문 섹션](#deterministic-enforcement) 참고.
