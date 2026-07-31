---
name: development
description: The standard procedure (Read → Think → Plan → Edit → Verify) for code work spanning multiple files or design judgment. Triggers - "add a feature", "refactor", "change this logic". Output is a verified minimal change. For one-line fixes or quick questions use quick-tasks; for unknown-cause bugs use debugging.
---

# Development

> Project commands and hard rules live in `AGENT.md`. This document covers **how to work**.

## Read -> Think -> Plan -> Edit -> Verify
1. **Read** — read the neighbouring code before changing it, so you follow this repo's conventions. Confirm a library exists via the manifest (imports, package file).
2. **Think** — see §Think before coding.
3. **Plan** — for 3+ steps or anything ambiguous, write the steps in `PLAN.md` **with a verify line per step**.
4. **Edit** — smallest change that works. Don't touch anything outside the request.
5. **Verify** — it isn't "done" until `.scripts/verify.sh` passes.

## Think before coding
The cheapest fix is the wrong code you never wrote.

- If two readings are both plausible, don't silently pick one — state both and ask. **One wrong silent assumption costs more than one question.**
- If you see a smaller way to solve the same problem, propose it before writing code.
- When stuck, name what's confusing and ask. Don't paper over confusion with guessed code.

```
Bad:   "add user data export" -> immediately writes csv/json/xml exporters
Good:  "Assuming an API endpoint, paginated JSON, PII fields excluded. Correct?"
```

## Goal-driven execution
LLMs loop reliably toward a verifiable goal and drift on vague imperatives.
Restate the task as **"do X → verify Y"**.

| Request as given | Restated goal |
|---|---|
| "add validation" | write a test for invalid input first → make it pass |
| "fix the bug" | write a test that reproduces it → make it pass |
| "refactor X" | existing tests pass both before and after |
| "make it faster" | write a benchmark with a target → hit it |

Weak success criteria ("make it work") need a human at every step. Strong ones let you finish alone.

When writing tests first, **watch each one fail before making it pass** — a test you never saw
fail may be re-checking existing behavior or measuring the wrong thing. Then write only the
minimal code that turns it green.

## No completion claims without evidence
"Should pass" and "probably fixed" are not reports. Before claiming anything, **run the command
that proves the claim, right here, and read its output.**

| Claim | Evidence |
|---|---|
| "tests pass" | test output from this session, 0 failures |
| "bug fixed" | the test that reproduced the symptom now passes |
| "requirements met" | a line-by-line checklist against the requirements |

(Credit: distilled from [obra/superpowers](https://github.com/obra/superpowers)
test-driven-development and verification-before-completion.)

## Branch strategy
> Workspace strategy: **{{FILL:dev.branch_strategy}}**

{{FILL:dev.branch_strategy_guide}}

## Conventions in this repo
- Drift or dead code you find outside your scope: don't fix it — note it in `.docs/plans/tech-debt.md` and move on.
- When judgment is unclear, decide from `.docs/design/core-beliefs.md`.
- Comment only when **WHY is non-obvious**, one line. WHAT is the name's job.
- Validate and escape input that comes from outside at the boundary (injection, path traversal, deserialization).
- Typechecks and tests only prove **code** correctness, not functional correctness — for UI changes,
  run the dev server and look at the golden path and regressions yourself. If you couldn't check, don't
  call it "working"; say so.

## Project-specific rules
{{FILL:dev.code_style_notes}}
