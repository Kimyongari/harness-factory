#!/usr/bin/env bash
# Deterministic guard for shell command calls. Wired to:
#   - Claude Code PreToolUse       (.claude/settings.json, matcher "Bash")
#   - Codex CLI hooks.PreToolUse   (.codex/config.toml, matcher "Bash")
#   - Cursor beforeShellExecution  (.cursor/hooks.json)
#
# Key idea: do NOT grep the raw JSON. First extract and decode the command
#           string to be run, then match danger patterns against the decoded
#           plain text.
#           (The old version grepped raw JSON as `"command":"[^"]*<pattern>`, so a
#            quoted argument before the dangerous token bypassed the guard entirely
#            — e.g. git commit -m "x" --no-verify.)
# On a block it prints the deny output for the detected tool schema and exits 0.
# Otherwise it exits 0 silently. To add rules, edit this file — the model cannot
# talk the runtime into turning it off.
set -uo pipefail

NEVER_TOUCH="{{FILL:dev.never_touch}}"

input=$(cat 2>/dev/null || true)

# --- Extract + JSON-decode the command string -------------------------------
# Claude/Codex put it in tool_input.command; Cursor in the top-level command.
# Both are "command":"..." so one extractor works. Escapes (\" \\) are kept while
# extracting and unescaped here. Whitespace after the colon is tolerated
# (absorbs serializer differences).
raw=$(printf '%s' "$input" \
  | grep -oE '"command"[[:space:]]*:[[:space:]]*"(\\.|[^"\\])*"' \
  | head -n 1 \
  | sed -E 's/^"command"[[:space:]]*:[[:space:]]*"//; s/"$//')
cmd=$(printf '%s' "$raw" | sed -E 's/\\n/ /g; s/\\t/ /g; s/\\r/ /g; s/\\"/"/g; s/\\\\/\\/g')

# No command to run (non-shell tool, etc.) — nothing to check.
[ -z "$cmd" ] && exit 0

# --- deny output: branch on tool schema -------------------------------------
# Cursor (beforeShellExecution) wants {"permission":"deny",...}; Claude/Codex want
# hookSpecificOutput.permissionDecision="deny". Both are emitted with exit 0.
_json_escape() { printf '%s' "$1" | sed -E 's/\\/\\\\/g; s/"/\\"/g'; }
if printf '%s' "$input" | grep -qE '"hook_event_name"[[:space:]]*:[[:space:]]*"beforeShellExecution"'; then
  deny() {
    msg=$(_json_escape "$1")
    printf '{"permission":"deny","agent_message":"%s","user_message":"%s"}\n' "$msg" "$msg"
    exit 0
  }
else
  deny() {
    msg=$(_json_escape "$1")
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$msg"
    exit 0
  }
fi

# Match only the decoded command. B: command/path boundary (also matches after a
# quote or separator so `bash -c "rm -rf …"` is caught, but excludes in-word
# substrings like the "rm" inside "charm").
has() { printf '%s' "$cmd" | grep -qE -- "$1"; }
B='(^|[^[:alnum:]_])'

# 1) Hook-bypass flags — never implicitly allow.
has '(--no-verify)'   && deny "Blocked: --no-verify skips commit hooks. Fix the underlying failure instead."
has '(--no-gpg-sign)' && deny "Blocked: --no-gpg-sign. Ask the user before turning off commit signing."

# 2) Irreversible core commands — require an explicit request.
has "${B}rm[[:space:]]+(-[[:alnum:]]*[rRfF]|--recursive|--force)" \
  && deny "Blocked: rm -rf. Narrow the deletion or get user confirmation."
has "${B}git[[:space:]]+reset[[:space:]]+--hard" \
  && deny "Blocked: git reset --hard discards work. Stash or branch first."
has "${B}git[[:space:]]+checkout[[:space:]]+\\.([[:space:]]|\$)" \
  && deny "Blocked: git checkout . discards local changes."
has "${B}git[[:space:]]+clean[[:space:]][^|;]*-[[:alnum:]]*[xX]" \
  && deny "Blocked: git clean -x/-X also deletes gitignored files (.env etc). Name the paths to remove."
has "${B}git[[:space:]]+branch[[:space:]][^|;]*(-[[:alnum:]]*D|--delete[[:space:]]+--force)" \
  && deny "Blocked: git branch -D discards unmerged commits. Use -d, or create a backup ref first."

# 2-a) Blanket staging - the most common path for a secret to reach a commit.
has "${B}git[[:space:]]+(add|stage)[[:space:]]+(-A|--all|\.)([[:space:]]|\$)" \
  && deny "Blocked: git add -A/. sweeps in files you didn't intend. Name the files explicitly."
has "${B}git[[:space:]]+commit[^|;]*[[:space:]]-[^-[:space:]]*a" \
  && deny "Blocked: git commit -a skips staging. Add the files by name instead."

# 2-b) force push — --force / trailing -f / +refspec all blocked (safe --force-with-lease allowed).
if has "${B}git[[:space:]].*push"; then
  has '(--force([^-]|$)|(^|[[:space:]])-f([[:space:]]|$)|[[:space:]]\+[^[:space:]:]+)' \
    && deny "Blocked: force push. Get explicit user confirmation. (Consider --force-with-lease if needed.)"
fi

# 2-c) Remote code execution / privilege escalation — blocked by default (explicit request only).
has '\|[[:space:]]*(sudo[[:space:]]+)?(ba)?sh([[:space:]]|;|&|$)' \
  && deny "Blocked: pipe-to-shell (e.g. curl … | sh) runs remote code without review."
has "${B}sudo[[:space:]]" \
  && deny "Blocked: sudo privilege escalation. Get user confirmation if truly needed."
has "${B}chmod[[:space:]]+([^[:space:]]+[[:space:]]+)*(0?777|a\\+rwx)" \
  && deny "Blocked: chmod 777/a+rwx grants excessive permissions."

# 3) Block writes/moves/deletes/staging of the survey's protected paths (dev.never_touch).
IFS=',' read -ra PATHS <<<"$NEVER_TOUCH"
for rawp in "${PATHS[@]:-}"; do
  p=$(printf '%s' "$rawp" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
  [ -z "$p" ] && continue
  esc=$(printf '%s' "$p" | sed -E 's/[][\\.^$*+?(){}|/]/\\&/g')
  has "${B}(rm|mv|cp|tee|chmod|chown|sed|truncate|dd|install)[[:space:]]+([^[:space:]]+[[:space:]]+)*${esc}" \
    && deny "Blocked: '${p}' is a never_touch path."
  has ">[[:space:]]*${esc}" \
    && deny "Blocked: output redirection to '${p}' (never_touch)."
  has "${B}git[[:space:]]+(add|stage)[[:space:]][^|]*${esc}" \
    && deny "Blocked: staging never_touch path '${p}' (prevents committing secrets)."
done

exit 0
