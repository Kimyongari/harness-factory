---
name: code-review
description: Use when asked to review code. Triggers - "look at this PR", "review this diff", "safe to merge?", change inspection. Input is a diff/branch/PR; output is a severity-ranked list of findings at file:line. If the job is to change code, use development.
---

# Code review

> Principle: **every finding ships with a reproducible failure story.** Not "this looks bad" but
> "with this input, it breaks like this".

## Procedure
1. **See the whole range**: `git diff <base>...HEAD` — never just the latest commit.
2. Sweep in severity order:
   - **Correctness**: is there an input/state this diff breaks? Boundaries, None, empty lists.
   - **Security**: does input reach shell/SQL/paths/deserialization? Do secrets land in code or logs?
   - **Regressions**: do existing callers change behavior? Do tests cover that path?
   - **Simplification**: can the same thing be done with less code (including existing utils)?
   - **Consistency**: does it break this repo's conventions (naming, error handling, comment density)?
3. Write each finding as `file:line — [severity] claim. Failure scenario.`
   Severity: **blocker** (incident/data loss) / **should** (fix before merge) / **nit** (taste, ignorable).

## Rules
- **Don't fix the code yourself** — a review request is not a fix request. Confirm before patching.
- If there are no findings, say so. Don't invent filler nits.
- Turn low-confidence findings into questions: "can X happen here?"
- Any blocker/should present → state the conclusion explicitly as "hold the merge".
