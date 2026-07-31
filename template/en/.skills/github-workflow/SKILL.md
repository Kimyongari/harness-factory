---
name: github-workflow
description: Safety rules for version control and collaboration. Triggers - "commit this", "open a PR", branching, pushing, issue handling. Output is named-file staging + conventional commits + PRs with Summary/Test plan. If the ask is only to judge a diff, use code-review.
---

# Git / GitHub

> Protected branch **{{FILL:gh.default_branch}}** · commit convention **{{FILL:gh.commit_convention}}** ({{FILL:gh.commit_language}}) · branch naming **{{FILL:gh.branch_naming}}**
> Use the `gh` CLI for GitHub operations.

## Git-specific prohibitions
On top of `AGENT.md`'s rules (confirm irreversible actions, no bypass flags):

- **Commit and push only when explicitly asked.** Editing code is not a request to commit it.
- Never force push to `{{FILL:gh.default_branch}}`. If asked, warn first.
- Stack a **new commit** instead of amending (unless the user asks for an amend). Amending after a
  failed hook can corrupt the previous commit.
- Don't modify git config.

## Staging
Name files explicitly instead of `git add -A` / `git add .`. Nearly every "we committed a secret"
incident starts on that one line. `{{FILL:dev.never_touch}}` is never staged.

Look before committing: `git status` · `git diff` · `git log --oneline -10` (to match this repo's style).

## Commit messages
Use the `{{FILL:gh.commit_convention}}` convention, written in {{FILL:gh.commit_language}}.
For conventional: `type(scope): subject` — `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.

Explain **why over what** in 1-2 sentences. Subject under 70 chars, detail in the body. Reflect the
actual diff; don't claim work you didn't do.

```bash
git commit -m "$(cat <<'MSG'
fix(payments): retry before the idempotency key expires

Stripe keeps idempotency keys for only 24h, so retries after that double-charged.
Cap the retry window at 23h to prevent it.
MSG
)"
```

## Pull requests
- Read the **full commit range** before writing: `git diff {{FILL:gh.default_branch}}...HEAD`. Don't write from the latest commit alone.
- Title under 70 chars. Body is `## Summary` + `## Test plan` (checklist).
- Pass the body via HEREDOC. **Return the PR URL** when done.
- Reference PRs and issues as full markdown URLs — never a bare `#123`.

## Unexpected state
Resolve merge conflicts rather than discarding one side. Investigate unfamiliar files, branches, or
lock files before deleting or overwriting — they may be the user's work in progress.
