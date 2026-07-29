# Harness reference - which check runs when

Read this **only when debugging or changing the harness**. Day-to-day work doesn't need it -
the checks fire on their own, and when one fails its output says what to fix.

## Runtime hooks

| When | Script | Role |
|---|---|---|
| Before every shell command | `.scripts/guard-bash.sh` | Blocks `rm -rf`, force push, `--no-verify`, pipe-to-shell (`curl\|sh`), privilege escalation (`sudo`/`chmod 777`), and any write or staging of never_touch paths |
| After a file edit | `.scripts/pre-commit.sh` | The lint/format/typecheck you picked in the survey |
| After every tool call | `.scripts/trace.sh` | Appends the tool-call trace to `.trace/tools.jsonl` (git-ignored) for failure analysis |
| Session start, resume, post-compaction | `.scripts/session-context.sh` | Re-injects branch, uncommitted changes, `PLAN.md` pointer |
| Just before compaction | `.scripts/precompact-note.sh` | Reminds you that compaction is lossy - persist state to `PLAN.md` |
| Before reporting "done" | `.scripts/verify.sh` | Runs `check-boundaries.sh` → `pre-commit.sh` → `post-commit.sh` in order |
| After a commit | `.scripts/post-commit.sh` | Heavier checks (usually tests) |
| Boundary check | `.scripts/check-boundaries.sh` | Detects reverse-direction imports against the layer order in `.docs/design/architecture.md` |

Don't reimplement these checks in the LLM. The scripts are the single source of truth.

## Tool-agnostic backstop - git hooks

Runtime hooks differ per tool, but git hooks fire on `git commit` / `git push`, so they apply
**no matter which agent commits**. Install once per clone:

```
git config core.hooksPath .githooks
```

- `.githooks/pre-commit` - `check-boundaries.sh` + `pre-commit.sh`
- `.githooks/pre-push` - rejects force pushes to the protected branch (`{{FILL:gh.default_branch}}`) + `post-commit.sh`

## Changing a check

| To change | Edit |
|---|---|
| Which lints/tests run | `.scripts/pre-commit.sh` · `.scripts/post-commit.sh` |
| What gets blocked | `.scripts/guard-bash.sh` (add rules here) |
| Layer boundaries | The allowed direction in `.docs/design/architecture.md` |
| Tool permissions / hook wiring | `.agents/agent.yaml` |
