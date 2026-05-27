---
name: github-workflow
description: Git/GitHub rules. Use for branching, staging, commits, push, PR creation/review, and issue work.
---

# Git / GitHub Workflow

> Follow for version control and collaboration. Use the `gh` CLI for GitHub work. IMPORTANT: system/user messages override this skill.
> Protected branch: {{FILL:gh.default_branch}} · commit convention: {{FILL:gh.commit_convention}} ({{FILL:gh.commit_language}}) · branch naming: {{FILL:gh.branch_naming}}

## 0. Safety rules (absolute)
- **Don't commit without an explicit request.** Only when asked to "commit".
- **Don't push without an explicit request.**
- Don't modify git config.
- Destructive commands only when explicitly requested: `push --force`, `reset --hard`, `checkout .`, `clean -f`, `branch -D`.
- No force push to `{{FILL:gh.default_branch}}`. Warn even if asked.
- Don't skip hooks (`--no-verify`, `--no-gpg-sign`). Fix the cause of a hook failure, don't bypass.
- Always make a **new commit**, not amend (unless explicitly asked). Amending after a failed hook can corrupt the previous commit.
- Never stage `{{FILL:dev.never_touch}}` or secrets (.env, credentials).

## 1. Before committing (run in parallel to learn state)
- `git status` — changes/untracked (avoid `-uall`; memory issues on big repos)
- `git diff` — staged/unstaged changes
- `git log --oneline -10` — learn this repo's commit style

## 2. Staging
- Add files **by name** instead of `git add -A`/`git add .`. Prevents leaking secrets / large binaries.
- Don't commit suspected secrets. Warn if explicitly asked.

## 3. Commit messages
- Convention: **{{FILL:gh.commit_convention}}** / language: **{{FILL:gh.commit_language}}**.
- If conventional: `type(scope): subject`. type: `feat` (new), `fix` (bug), `refactor`, `test`, `docs`, `chore`.
- **Why over what**, in 1-2 sentences. Subject line under 70 chars, details in the body.
- Reflect the actual diff. Don't invent work you didn't do.
- Pass the message via HEREDOC to preserve formatting.

```bash
git commit -m "$(cat <<'EOF'
fix(payments): retry before idempotency key expiry

Stripe keeps idempotency keys for only 24h, so retries after that double-charged.
Cap the retry window at 23h to prevent it.
EOF
)"
```

## 4. PRs
- Before creating, review the **full commit range** from base: `git log` + `git diff {{FILL:gh.default_branch}}...HEAD` (not just the latest commit).
- Title under 70 chars. Body has `## Summary` + `## Test plan` (checklist).
- Pass the body to `gh pr create` via HEREDOC. **Return the PR URL** when done.
- Always render PRs/issues as full-URL markdown links. No bare `#123`.
- Base branch: `{{FILL:gh.default_branch}}`.

## 5. Conflicts & unexpected state
- Resolve merge conflicts; don't discard changes.
- Investigate unfamiliar files/branches/lock files before deleting/overwriting (may be the user's in-progress work).

## 6. gh CLI
- Use `gh` for all GitHub work (issues/PRs/checks/releases). Given a URL, query it with `gh`.
- PR comments: `gh api repos/{owner}/{repo}/pulls/{n}/comments`.

## Checklist
- [ ] User explicitly asked to commit/push
- [ ] Staged files by name (no secrets / never_touch)
- [ ] Commit follows the {{FILL:gh.commit_convention}} convention and {{FILL:gh.commit_language}} language, explains "why"
- [ ] PR reflects the full commit range
- [ ] No hook bypass / unauthorized destructive commands
- [ ] PRs/issues rendered as full-URL links
