---
name: development
description: Core rules for writing, modifying, refactoring, and debugging code. Use when implementing features, fixing bugs, writing tests, or verifying.
---

# Development

> Follow when writing/modifying/verifying code. IMPORTANT: system/user messages override this skill.
> Project commands are in `AGENT.md`'s table; never-touch paths are `{{FILL:dev.never_touch}}`.

## 0. Think before coding (the cheapest fix is to not write the wrong code)
- **State assumptions explicitly.** If you have to guess what the user meant, say what you assumed.
- **Surface ambiguity — don't pick silently.** If two interpretations both fit, list them and ask. One wrong silent pick costs more than one clarifying question.
- **Push back when a simpler approach exists.** Don't just execute what was asked if a smaller change solves the same problem.
- **Stop when confused.** Name what's unclear and ask. Don't paper over confusion with speculative code.

```
Bad:  "Add a feature to export user data" → starts writing csv/json/xml exporters.
Good: "I'll assume API endpoint returning paginated JSON, all non-PII fields, no file output.
       Confirm before I implement? Three other readings of 'export' are possible — list them?"
```

## Workflow (Read -> Think -> Plan -> Edit -> Verify)
1. **Read** — before changing anything, read adjacent code/patterns and follow this repo's conventions. Confirm libraries exist (imports/package manifest).
2. **Think** — apply §0. If anything is ambiguous, ask *before* writing code.
3. **Plan** — for 3+ steps or anything ambiguous, write the steps in `PLAN.md` with a verify line each (see §Goal-driven execution).
4. **Edit** — minimal change, per the rules below.
5. **Verify** — pass `.scripts/verify.sh`. No "done" before it passes.

## Branch strategy (workspace)
> Workspace strategy: **{{FILL:dev.branch_strategy}}**

{{FILL:dev.branch_strategy_guide}}

## Scope discipline (the most common failure mode)
- **Do only what was asked.** No drive-by cleanup in a bug fix.
- Three similar lines beat a premature abstraction. Don't design for hypothetical futures.
- Edit existing files > create new ones. Don't leave half-finished work.
- Found drift/dead code? Don't fix it — log it in `.docs/plans/tech-debt.md` and move on (out-of-scope cleanup is a separate PR).

## Goal-driven execution (turn imperatives into verifiable goals)
LLMs loop reliably toward a checkable goal; they drift on vague imperatives. Restate every task as **"do X → verify Y"**.

| Imperative ask | Verifiable goal |
|---|---|
| "Add validation" | Write tests for invalid inputs → make them pass |
| "Fix the bug" | Write a test that reproduces it → make it pass |
| "Refactor X" | Ensure existing tests pass before and after |
| "Make it faster" | Write a benchmark with a target → meet it |

For multi-step work, write the plan as a verify-line-per-step in `PLAN.md`:
```
1. Add idempotency check       → verify: new unit test passes; existing payment tests still green
2. Wire into webhook handler   → verify: integration test for duplicate webhook passes
3. Add 24h key expiry          → verify: time-travel test confirms expiry; verify.sh green
```

Weak criteria ("make it work") require constant human review. Strong criteria let you loop without it.

## Decision table — when unsure
| Situation | Do | Don't |
|---|---|---|
| Input validation | only at system boundaries (user input, external API) | defensive code on every internal call |
| Error handling | only for failures that can actually happen | try/except for impossible cases |
| Duplicate code | extract after 3+ repetitions | abstract eagerly at 2 |
| Unused code | delete completely if certain | rename to `_unused`, leave "// removed" |
| Adding a library | prefer existing dependencies | add a new dep for something trivial |
| Compatibility | just change the code | keep old paths via feature flags/shims |

## Comments (default: none)
- Only when the WHY is non-obvious (hidden constraint, subtle invariant, bug workaround, surprising behavior).
- Never explain WHAT — good names do that. No caller/issue-number/"used by X" comments (they rot as code changes).

```python
# Bad: explains WHAT, rots quickly
# takes user_id and fetches the user (#412 payments team request)
def get_user(user_id): ...

# Good: no comment. The name says it.
def get_user(user_id): ...

# Good: only when WHY is non-obvious
# Stripe keeps idempotency keys for 24h, so retry within that window to avoid double charges.
def retry_charge(...): ...
```

## Security (at the boundary)
- Don't introduce OWASP Top 10 issues. Fix unsafe code the moment you notice it.
- No hard-coded secrets -> env vars / secret manager. Never read or write `{{FILL:dev.never_touch}}`.
- Validate/escape external input at the boundary (injection / XSS / SQLi).

## Deterministic tools first (don't send the LLM to do a linter's job)
- Run format/lint/typecheck via the `AGENT.md` commands. Don't eyeball style.
- Prefer fast, exact deterministic tools over the slow, expensive LLM.

## Verification (required)
- Passing `.scripts/verify.sh` is the definition of "done".
- Typecheck/tests verify **code correctness**, not **feature correctness**.
- For UI/frontend changes, run the dev server and verify behavior in a browser (golden path, edge cases, regressions). If you can't test the UI, say so — don't claim success.

## Handling obstacles
- Don't take destructive shortcuts (`--no-verify`, bypassing safety). Fix the **root cause**, not the symptom.

## Project-specific rules (from survey)
{{FILL:dev.code_style_notes}}

## Checklist (before submitting)
- [ ] Surfaced ambiguity before coding (or had none) — no silent picks
- [ ] Followed existing patterns/conventions
- [ ] No changes/abstractions beyond the requested scope
- [ ] No defensive code for impossible cases
- [ ] Comments explain WHY only, or none at all
- [ ] No secret/injection risks, didn't touch `{{FILL:dev.never_touch}}`
- [ ] Task framed as "do X → verify Y" — success criterion is checkable, not vibes
- [ ] Passed `.scripts/verify.sh`
- [ ] (If UI) verified behavior and regressions in a browser
