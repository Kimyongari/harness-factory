#!/usr/bin/env bash
# Task-completion verification pipeline (the heart of the feedback loop).
# The agent MUST pass this before reporting a task "done".
#
# Design principle (harness engineering):
# - Output is a checklist: one ✓ line per passing step; only failing steps print
#   their output plus a "next action". (This runs on every Stop hook, so verbose
#   success output is a recurring token cost. The agent should aim precisely at
#   the failing item — the information lives in failures.)
set -uo pipefail

# When run as a Stop hook, the runtime passes hook JSON on stdin. If the previous
# Stop hook already blocked (stop_hook_active=true), exit cleanly so a permanently
# failing check (e.g. a tool missing from PATH) can't trap the agent in a loop.
# Skip the read when stdin is a terminal (manual `.scripts/verify.sh` runs).
if [ ! -t 0 ]; then
  _hook_input=$(cat 2>/dev/null || true)
  case "$_hook_input" in
    *'"stop_hook_active"'*true*) exit 0 ;;
  esac
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAILED=0

run_step() { # $1=name $2=next action on failure, $3...=command to run
  local name="$1" next="$2" out
  shift 2
  if out=$("$@" 2>&1); then
    echo "PASS $name"
  else
    echo "FAIL $name"
    printf '%s\n' "$out"
    echo "   next action: $next"
    FAILED=1
  fi
}

echo "[verify] verification checklist"

# 1) architecture boundaries  2) pre-commit (survey presets: lint/format/types)  3) post-commit (tests etc.)
[ -x "$SCRIPT_DIR/check-boundaries.sh" ] && \
  run_step "architecture boundaries" "apply the 'fix' from the check-boundaries output above" "$SCRIPT_DIR/check-boundaries.sh"
[ -f "$SCRIPT_DIR/pre-commit.sh" ] && \
  run_step "pre-commit (lint/format/types)" "run the FAIL-marked command directly and fix the cause" bash "$SCRIPT_DIR/pre-commit.sh"
[ -f "$SCRIPT_DIR/post-commit.sh" ] && \
  run_step "post-commit (tests)" "read the failing test output and fix the cause" bash "$SCRIPT_DIR/post-commit.sh"

if [ "$FAILED" -ne 0 ]; then
  echo "[verify] verification FAILED — do only the 'next action' of FAIL items, then re-run."
  exit 1
fi
echo "[verify] all checks passed"
