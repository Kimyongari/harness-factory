# AGENT.md

<!-- This file is loaded into every session. Keep only universally applicable rules here. -->
<!-- Anti-pattern: the encyclopedia. If everything is "important", nothing gets followed. Keep under 500 lines. -->
<!-- Push details to per-task docs/skills; here, just tell the agent how to find them (progressive disclosure). -->

## Project
- Name: {{FILL:project.name}}
- Description: {{FILL:project.description}}
- Language: {{FILL:project.language}} {{FILL:project.language_version}}
- Framework: {{FILL:project.framework}} · package manager: {{FILL:project.package_manager}}
- Agent role: {{FILL:profile.role}} ({{FILL:profile.expertise}})

## Commands (do NOT replace deterministic tools with the LLM)
| Purpose | Command |
|---|---|
| Install | `{{FILL:dev.install_cmd}}` |
| Run | `{{FILL:dev.run_cmd}}` |

## Mechanical enforcement (runtime, not prompt)
The runtime (Claude Code / Codex) fires these scripts deterministically — they apply even if the LLM "forgets". Don't try to bypass.

| When | Script | What it does |
|---|---|---|
| Before any `Bash` call | `.scripts/guard-bash.sh` | Blocks `rm -rf`, force push, `--no-verify`, pipe-to-shell (`curl\|sh`), privilege escalation (`sudo`/`chmod 777`), and writes/staging of never-touch paths (PreToolUse) |
| After `Edit` / `Write` / `MultiEdit` | `.scripts/pre-commit.sh` | Runs the lint/format/typecheck checks you picked (PostToolUse) |
| Before reporting "done" | `.scripts/verify.sh` | Runs `check-boundaries.sh` → `pre-commit.sh` → `post-commit.sh`; failure prints a fix hint (Stop) |
| Architecture boundary check | `.scripts/check-boundaries.sh` | Detects reverse-direction imports based on `dev.architecture_layers` |
| Post-commit (usually tests) | `.scripts/post-commit.sh` | Runs the heavier checks you picked |

Cursor: per-skill `.cursor/rules/*.mdc` use `globs` for code/doc files so they auto-attach without LLM judgment; `00-overview.mdc` is `alwaysApply: true`. **But Cursor has no runtime hooks, so the `.scripts/*` above do NOT auto-run — in Cursor these rules are advisory.** Tool-agnostic enforcement comes from the git hooks below.

### Tool-agnostic backstop — git hooks (recommended)
git hooks fire on `git commit` / `git push`, so they apply no matter which agent committed (Cursor included). Install once per clone:

```
git config core.hooksPath .githooks
```

- `.githooks/pre-commit` — runs `check-boundaries.sh` + `pre-commit.sh` (lint/format/typecheck).
- `.githooks/pre-push` — rejects force (non-fast-forward) pushes to the protected branch (`{{FILL:gh.default_branch}}`) and runs `post-commit.sh` (tests).

Don't re-implement these checks via the LLM. Use them as the source of truth.

## Absolute rules (always apply)
1. **Surface assumptions before implementing.** If two readings of the request both fit, list them and ask — don't pick silently. If a simpler approach exists, say so before coding.
2. **Do only what was asked.** No drive-by refactors, no designing for hypothetical futures.
3. **Frame the task as "do X → verify Y".** Vague success criteria ("make it work") force constant clarification. Restate as a checkable goal — see `.skills/development/SKILL.md`'s Goal-driven execution section.
4. Prefer editing existing files over creating new ones.
5. Before reporting a task "done", you MUST pass `.scripts/verify.sh`.
6. **Never modify or commit these paths**: `{{FILL:dev.never_touch}}` (also enforced by `.scripts/guard-bash.sh`).
7. Irreversible actions (push, delete, deploy, merge) require user confirmation first.
8. If the same mistake recurs, don't just fix it once — add a rule/check to the environment that prevents it.

## What to read, when (progressive disclosure)
| Situation | Read |
|---|---|
| Not sure which doc you need | `.docs/index.md` |
| Coding / verifying / refactoring | `.skills/development/SKILL.md` |
| Writing docs / README / comments / summaries | `.skills/doc-writing/SKILL.md` |
| Web search / fact-finding | `.skills/web-research/SKILL.md` |
| Commits / PRs / branches | `.skills/github-workflow/SKILL.md` |
| Design beliefs & architecture boundaries | `.docs/design/` |
| Feature / API specs | `.docs/specs/` |
| In-progress work & tech debt | `.docs/plans/`, root `PLAN.md` |
| Tools / permissions / hooks / verification | `.agents/agent.yaml` |

## Context hygiene
- Load context **selectively**. Don't read unrelated docs up front; pull them just-in-time via `.docs/index.md`.
- The context window is finite — **recall degrades as it fills (context rot)**. Clear context (`/clear` etc.) when moving to an unrelated task.
- For multi-step work, record decisions/state **explicitly in `PLAN.md`** — don't rely on the context "remembering". Auto-summarization (compaction) is lossy, so always persist key decisions to a file.
- For file-heavy investigation or independent verification of finished work, delegate to a **separate-context subagent** to keep the main context clean (where the tool supports it).
- Treat verification failures as fix instructions: read the cause + next action, then fix → `.scripts/`.
- When a judgment call is ambiguous, decide using `.docs/design/core-beliefs.md`.
