#!/usr/bin/env bash
# Tool-call trace — the runtime invokes this after every tool call. Wired at:
#   - Claude Code PostToolUse  (.claude/settings.json, matcher "*")
#   - Codex CLI hooks.PostToolUse (.codex/config.toml)
#
# Extracts just the tool name/command from the hook JSON on stdin and appends
# one line per call to .trace/tools.jsonl.
# Why: agent failures are hard to reproduce — you need the trajectory on disk
#      to analyze causes and tune the harness (which tools/commands fail often).
# .trace/ is in .gitignore (never committed). Safe to delete at any time.
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TRACE_FILE="$ROOT/.trace/tools.jsonl"
MAX_BYTES=10485760  # rotate one generation past 10MB (prevents unbounded growth)

input=$(cat 2>/dev/null || true)
[ -z "$input" ] && exit 0

extract_str() {
  # Pull the JSON string literal of "key": "..." verbatim (quotes included),
  # escapes preserved — so it can be embedded back into JSON without re-escaping.
  printf '%s' "$input" | grep -oE "\"$1\"[[:space:]]*:[[:space:]]*\"(\\\\.|[^\"\\\\])*\"" \
    | head -n 1 | sed -E "s/^\"$1\"[[:space:]]*:[[:space:]]*//"
}

tool=$(extract_str tool_name)
event=$(extract_str hook_event_name)
cmd=$(extract_str command)
[ -z "$tool" ] && tool='"unknown"'
[ -z "$event" ] && event='"PostToolUse"'

mkdir -p "$(dirname "$TRACE_FILE")"
if [ -f "$TRACE_FILE" ] && [ "$(wc -c <"$TRACE_FILE")" -gt "$MAX_BYTES" ]; then
  mv "$TRACE_FILE" "$TRACE_FILE.1"
fi

line="{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"event\":$event,\"tool\":$tool"
[ -n "$cmd" ] && line="$line,\"command\":$cmd"
printf '%s}\n' "$line" >>"$TRACE_FILE"
exit 0
