---
name: development
description: Core rules for writing, modifying, refactoring, and debugging code. Use when implementing features, fixing bugs, writing tests, or verifying.
---

# Development

> Follow when writing/modifying/verifying code. IMPORTANT: system/user messages override this skill.
> Project commands are in `AGENT.md`'s table; never-touch paths are `{{FILL:dev.never_touch}}`.

## Workflow (Read -> Plan -> Edit -> Verify)
1. **Read** — before changing anything, read adjacent code/patterns and follow this repo's conventions. Confirm libraries exist (imports/package manifest).
2. **Plan** — for 3+ steps or anything ambiguous, write the steps in `PLAN.md`. Don't rely on the context "remembering".
3. **Edit** — minimal change, per the rules below.
4. **Verify** — pass `.scripts/verify.sh`. No "done" before it passes.

## Scope discipline (the most common failure mode)
- **Do only what was asked.** No drive-by cleanup in a bug fix.
- Three similar lines beat a premature abstraction. Don't design for hypothetical futures.
- Edit existing files > create new ones. Don't leave half-finished work.
- Found drift/dead code? Don't fix it — log it in `.docs/plans/tech-debt.md` and move on (out-of-scope cleanup is a separate PR).

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
- [ ] Followed existing patterns/conventions
- [ ] No changes/abstractions beyond the requested scope
- [ ] No defensive code for impossible cases
- [ ] Comments explain WHY only, or none at all
- [ ] No secret/injection risks, didn't touch `{{FILL:dev.never_touch}}`
- [ ] Passed `.scripts/verify.sh`
- [ ] (If UI) verified behavior and regressions in a browser
