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
| Test | `{{FILL:dev.test_cmd}}` |
| Lint | `{{FILL:dev.lint_cmd}}` |
| Format | `{{FILL:dev.format_cmd}}` |
| Run | `{{FILL:dev.run_cmd}}` |

## Absolute rules (always apply)
1. **Do only what was asked.** No drive-by refactors, no designing for hypothetical futures.
2. Prefer editing existing files over creating new ones.
3. Before reporting a task "done", you MUST pass `.scripts/verify.sh`.
4. **Never modify or commit these paths**: `{{FILL:dev.never_touch}}`
5. Irreversible actions (push, delete, deploy, merge) require user confirmation first.
6. If the same mistake recurs, don't just fix it once — add a rule/check to the environment that prevents it.

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
- Load context **selectively**. Don't read unrelated docs up front.
- For multi-step work, record decisions/state **explicitly in `PLAN.md`** — don't rely on the context "remembering" (long chains lose context).
- Treat verification failures as fix instructions: read the cause + next action, then fix → `.scripts/`.
- When a judgment call is ambiguous, decide using `.docs/design/core-beliefs.md`.
