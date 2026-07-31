---
name: debugging
description: Use when hunting the cause of a bug, error, or failing test — and before proposing any fix. Triggers - "why doesn't this work", stack traces, flaky failures, regressions ("worked yesterday"). Output is reproduce → root cause → minimal fix → regression test. If you already know the cause and just need the fix, use development.
---

# Debugging

**Iron law: no fixes before the root cause is established.** Symptom patches are failure —
and under time pressure, guess-and-patch thrashing is *slower* than working systematically.

## Procedure (in order)
1. **Read the error to the end.** Stack traces from the bottom (origin) up. The answer is often
   already there.
2. **Reproduce first.** Get the smallest command/input that re-triggers the failure and, when
   possible, pin it as a **failing test** — that becomes the definition of done. Can't reproduce?
   Don't fix; gather more evidence.
3. **Check recent changes.** `git diff`, recent commits, dependencies, environment. If it worked
   yesterday, the environment (versions, PATH, env vars) changed more often than the code.
4. **Compare against a working example.** Find similar code in this repo that works and list
   every difference. Don't filter with "that can't matter" — the filtered one usually does.
5. **One hypothesis → smallest test.** Write it as a sentence: "X is the cause because Y."
   One variable at a time. If it fails, form a new hypothesis — never stack fixes on fixes.
   In multi-layer systems (API → service → DB), instrument each boundary and get **evidence of
   which layer breaks** before touching code.
6. **Say the root cause in one sentence**, then apply the minimal fix and let the test from
   step 2 turn green. No drive-by cleanups.

## Red flags — stop and return to step 1
- "Let me just try this first and investigate later"
- "It's probably X, let me fix that"
- "Change a few places, run the tests once"
- "I don't fully understand, but this might work"
- Listing fixes before tracing the data flow

## The three-strike rule
**Stop after 3 failed fix attempts.** It's time to question the architecture, not attempt
fix #4 — when every fix surfaces a new symptom somewhere else, the hypothesis isn't wrong,
the structure is. Write up hypotheses tried/refuted, report, and confirm direction.

| Rationalization | Reality |
|---|---|
| "Simple bug, the process is overkill" | Simple bugs have root causes too; the process is fast when it's simple |
| "No time — patch first" | The first patch sets the pattern. Thrashing is slower |
| "I'll write the test after the fix" | A test you never saw fail verifies nothing |

> Credit: compressed and restructured from
> [obra/superpowers](https://github.com/obra/superpowers) systematic-debugging.
