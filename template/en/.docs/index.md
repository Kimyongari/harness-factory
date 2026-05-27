# .docs index (context router)

> The agent reads **only the docs it needs**. Don't load everything into context at once.
> This index is a map for "which doc do I need for what I'm about to do".

## Routing by task

| What you're about to do | Read first |
|---|---|
| Understand architecture/design decisions | `design/architecture.md`, `design/core-beliefs.md` |
| Check feature/API behavior | `specs/` (e.g. `specs/api_specs.md`) |
| See in-progress work / tech debt | `plans/` (e.g. `plans/tech-debt.md`), root `PLAN.md` |
| Reference external libs / design system | `references/` |

## Directory roles
- **design/** — unchanging design beliefs and architecture boundaries. The single source of truth for "why it's built this way".
- **specs/** — product/feature/API specs. "What must behave how".
- **plans/** — execution plans, tech-debt tracker. Living docs that change over time.
- **references/** — external material (lib doc excerpts, `llms.txt`). Excerpts only, to save tokens.

## Principles (harness engineering)
- **Hierarchy**: no giant single file. Split into small docs close to the work.
- **Selective loading**: don't pre-read unrelated docs. Tokens = cost.
- **Single source of truth**: don't duplicate the same fact across docs. Link instead.
