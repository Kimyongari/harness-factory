---
name: quick-tasks
description: Token-saving mode for everyday lightweight work. Use for one-line fixes, typo/config-value changes, quick questions ("what does this function do?"), throwaway scripts, and anything that ends inside a single file. Output is a minimal diff and a short report. For multi-file, design, or new-feature work, switch to the development skill.
---

# Daily / lightweight tasks (token saving)

> Purpose: **don't spend a big process on a small request.** Safety rules (AGENT.md, hooks)
> stay in force; only the process gets lighter.

## Qualification — may this run in light mode?
Proceed in light mode only if ALL hold:
- You already know the target file, or one search pins it down
- There is no design decision (you are fixing, not choosing behavior)
- The diff is roughly under 20 lines

If any fails, switch to the `development` skill (Read → Think → Plan → Edit → Verify).
**Announce the switch** — one line like "scope grew, switching to the normal process".

## Light-mode rules
- **Minimal reading**: open only the target file (and what it directly references). No pre-emptive browsing.
- **Skip the plan doc**: don't create or update `PLAN.md`. The moment steps appear, this isn't light mode.
- **No drive-by changes**: don't do refactors you happen to notice. One line in `.docs/plans/tech-debt.md`, move on.
- **Report in ≤3 sentences**: what changed, how you verified. No background essays or option lists.
- **Never skip verification**: passing `.scripts/verify.sh` defines "done" in light mode too.
  (The hook enforces it anyway — don't try to route around it.)

## Examples
| Request | Handling |
|---|---|
| "bump the timeout to 5s" | locate the constant → edit → verify → one-line report |
| "what's this error?" | read only the file in the stack, explain the cause (don't fix until asked) |
| "fix the README typo" | edit → verify → done |
| "change the login flow" | not light — announce switch to development and proceed |
