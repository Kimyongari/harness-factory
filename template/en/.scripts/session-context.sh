#!/usr/bin/env bash
# Session-start context injection — the runtime calls this on session start/resume/
# clear/after-compaction.
#   - Claude Code SessionStart (.claude/settings.json)
#   - Codex CLI hooks.SessionStart (.codex/config.toml)
#
# Why: long sessions lose context (especially after auto-compaction) and the agent
#      forgets in-progress work and current state. Re-inject a progress pointer at
#      the start of every session.
# stdout is injected as context for this event, so print plain text (no JSON needed).
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

echo "## Session context (auto-injected)"
if git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  branch=$(git -C "$ROOT" branch --show-current 2>/dev/null)
  echo "- Branch: ${branch:-(detached)}"
  changed=$(git -C "$ROOT" status --short 2>/dev/null | head -n 20)
  if [ -n "$changed" ]; then
    echo "- Uncommitted changes:"
    printf '%s\n' "$changed" | sed 's/^/    /'
  else
    echo "- Uncommitted changes: none"
  fi
fi
[ -f "$ROOT/PLAN.md" ] && echo "- Resume in-progress work from PLAN.md (auto-compaction is lossy, so state lives in PLAN.md)."
echo "- If unsure which doc you need, route via .docs/index.md (read just-in-time, not up front)."
exit 0
