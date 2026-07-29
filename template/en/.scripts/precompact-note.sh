#!/usr/bin/env bash
# Pre-compaction reminder — the runtime calls this right before auto/manual
# context compaction.
#   - Claude Code PreCompact (.claude/settings.json)
#   - Codex CLI hooks.PreCompact (.codex/config.toml)
#
# Why: compaction is lossy. Key decisions / open issues that live only in context
#      are dropped. Remind the agent to persist state to PLAN.md first. (Does not
#      block — reminder only.)
set -uo pipefail
echo "[precompact] Context is about to be compacted (lossy). Make sure key decisions, open issues, and next steps are written to PLAN.md. After compaction, SessionStart re-injects the PLAN.md pointer."
exit 0
