#!/usr/bin/env bash
# Deterministic guard for Bash tool calls. Wired to:
#   - Claude Code's PreToolUse  (.claude/settings.json, matcher "Bash")
#   - Codex CLI's hooks.PreToolUse (.codex/config.toml, matcher "Bash")
#
# Reads the tool-call JSON on stdin, emits a JSON "deny" verdict on a match.
# Exits 0 silently when the command looks fine — that lets the normal
# permission flow take over.
#
# Why a separate script: the rules below run BEFORE the LLM sees the call,
# so it cannot talk the runtime out of them. Edit this file to extend.
set -uo pipefail

NEVER_TOUCH="{{FILL:dev.never_touch}}"
PROTECTED_BRANCH="{{FILL:gh.default_branch}}"

input=$(cat 2>/dev/null || true)

deny() {
  # JSON shape per Claude Code / Codex hooks reference.
  cat <<EOF
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"$1"}}
EOF
  exit 0
}

contains() { printf '%s' "$input" | grep -qE "$1"; }

# Both Claude Code and Codex deliver the command string in tool_input.command as a
# single JSON object on stdin. Tolerate whitespace around the colon so we match
# whether the serializer emits "command"[[:space:]]*:[[:space:]]*"x" or "command": "x" — otherwise the guard
# would silently pass everything (a no-op security check).

# 1) Hook-bypass flags — never silently allowed.
contains '"command"[[:space:]]*:[[:space:]]*"[^"]*--no-verify'       && deny "blocked: --no-verify bypasses commit hooks. Fix the failure instead of skipping."
contains '"command"[[:space:]]*:[[:space:]]*"[^"]*--no-gpg-sign'     && deny "blocked: --no-gpg-sign. Ask the user explicitly before disabling commit signing."

# 2) Destructive defaults — must be explicit.
contains '"command"[[:space:]]*:[[:space:]]*"[^"]*\brm[[:space:]]+-[rRfF]+\b' && deny "blocked: rm -rf. Use a more targeted delete or confirm with the user."
contains '"command"[[:space:]]*:[[:space:]]*"[^"]*\bgit[[:space:]]+push[[:space:]]+(--force|-f[[:space:]])' && deny "blocked: force push. Ask the user explicitly."
contains '"command"[[:space:]]*:[[:space:]]*"[^"]*\bgit[[:space:]]+reset[[:space:]]+--hard'                && deny "blocked: git reset --hard would discard work. Stash or branch first."
contains '"command"[[:space:]]*:[[:space:]]*"[^"]*\bgit[[:space:]]+checkout[[:space:]]+\.[[:space:]]*\\?"'  && deny "blocked: git checkout . would discard local changes."

# 3) Force-push to the protected branch — always refuse.
if [ -n "$PROTECTED_BRANCH" ]; then
  contains "\"command\"[[:space:]]*:[[:space:]]*\"[^\"]*\\bgit[[:space:]]+push[[:space:]]+[^\"]*${PROTECTED_BRANCH}\\b[^\"]*(--force|-f[[:space:]])" \
    && deny "blocked: push to '$PROTECTED_BRANCH' with --force."
fi

# 4) Write/move/remove against protected paths from the survey (dev.never_touch).
IFS=',' read -ra PATHS <<<"$NEVER_TOUCH"
for raw in "${PATHS[@]:-}"; do
  p=$(printf '%s' "$raw" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
  [ -z "$p" ] && continue
  esc=$(printf '%s' "$p" | sed -E 's/[][\\.^$*+?(){}|/]/\\&/g')
  contains "\"command\"[[:space:]]*:[[:space:]]*\"[^\"]*\\b(rm|mv|cp|tee|chmod|chown)\\b[^\"]*${esc}" \
    && deny "blocked: '${p}' is listed as never_touch."
  contains "\"command\"[[:space:]]*:[[:space:]]*\"[^\"]*>[[:space:]]*${esc}" \
    && deny "blocked: redirecting output into '${p}' (never_touch)."
done

exit 0
