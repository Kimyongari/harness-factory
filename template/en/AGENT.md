# AGENT.md

<!-- Loaded on every request. Tokens here are a cost you pay each time. -->
<!-- Leave out: facts you can read off the filesystem, generic good practice, hook internals. -->
<!-- Keep in: what is true only in this repo, what is hard to undo, and where to look next. -->

## Project
**{{FILL:project.name}}** — {{FILL:project.description}}
{{FILL:project.language}} {{FILL:project.language_version}} · {{FILL:project.framework}} · {{FILL:project.package_manager}}

| Purpose | Command |
|---|---|
| Install | `{{FILL:dev.install_cmd}}` |
| Run | `{{FILL:dev.run_cmd}}` |
| Verify | `.scripts/verify.sh` — **this is the definition of "done"** |

## Gotchas in this repo
{{FILL:dev.gotchas}}

## Rules that hold
1. Pass `.scripts/verify.sh` before saying "done". If it didn't pass, say so.
2. Never read, write, or commit `{{FILL:dev.never_touch}}`.
3. Irreversible actions (push, delete, deploy, merge) need user confirmation first.
4. When a check blocks you, **fix the cause.** Don't pass it with a bypass flag (`--no-verify` etc).
5. If the same mistake happens twice, add a check that prevents it instead of fixing it again.

These checks run as **runtime hooks**, not prompts — they fire even if you forget, and you cannot
talk them out of it. Which hook fires when: `.docs/references/harness.md`.
<!--TARGET_ENFORCEMENT-->

## Where to look
| Situation | Document |
|---|---|
| Coding, debugging, refactoring | `.skills/development/SKILL.md` |
| Commits, PRs, branches | `.skills/github-workflow/SKILL.md` |
| Docs, READMEs, summaries | `.skills/doc-writing/SKILL.md` |
| Web research, fact-checking | `.skills/web-research/SKILL.md` |
| Design beliefs, architecture boundaries | `.docs/design/` |
| Specs · work in progress · tech debt | `.docs/specs/` · `PLAN.md` · `.docs/plans/tech-debt.md` |
| Don't know where to look | `.docs/index.md` |

Write decisions from multi-step work into `PLAN.md`. Compaction is lossy, so a decision that
lives only in context is a decision you will lose.
