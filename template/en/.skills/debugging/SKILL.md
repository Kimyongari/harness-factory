---
name: debugging
description: Use when hunting the cause of a bug, error, or failing test. Triggers - "why doesn't this work", stack traces, flaky failures, regressions ("worked yesterday"). Output is reproduce → root cause → minimal fix → regression test. If you already know the cause and just need the fix, use development.
---

# Debugging

> Principle: **fix causes, not symptoms.** Repeated guess-and-patch is the most expensive path.

## Procedure (in order)
1. **Reproduce first.** Get the smallest command/input that re-triggers the failure. Without a
   repro, both the fix and its verification are guesses.
   - When possible, pin the repro as a **failing test** — that becomes the definition of done.
2. **Collect evidence.** Read stack traces from the bottom (origin) up. Before searching the web
   for the error text, grep this repo — the same failure may already have a handled precedent.
3. **Hypothesis → bisect.** Halve the suspect space: half the input, half the commits
   (`git bisect`), half the code path (early return / logging). Change one variable at a time.
4. **State the root cause in one sentence.** If you can't say "Z crashes because X is None when
   Y", you don't know it yet.
5. **Minimal fix + regression test.** Done = the failing test from step 1 turns green. Don't
   clean up unrelated code on the way.

## Pitfalls
- **Don't swallow errors**: `except: pass` is the opposite of debugging. Name the exception you
  catch; let the rest propagate.
- **Flaky failures**: suspect ordering, timing, shared state. Measure frequency with repeated runs first.
- **Environment before code** (versions, PATH, env vars) — if it worked yesterday, the
  environment changed more often than the code did.
- No progress for 10+ minutes → write up hypotheses tried/refuted, report, and confirm direction.
