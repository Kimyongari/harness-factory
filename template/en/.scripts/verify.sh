#!/usr/bin/env bash
# Task-completion verification pipeline (the heart of the feedback loop).
# The agent MUST pass this before reporting a task "done".
#
# Design principle (harness engineering):
# - On failure, print the cause AND the next action, not just "pass/fail".
# - That lets the agent self-correct without human intervention.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAILED=0

step() { echo ""; echo "-- $1 --"; }
fail() { echo "FAIL: $1"; echo "   next action: $2"; FAILED=1; }

echo "[verify] starting verification pipeline..."

# 1) Architecture boundaries
step "architecture boundaries"
if [ -x "$SCRIPT_DIR/check-boundaries.sh" ]; then
  if ! "$SCRIPT_DIR/check-boundaries.sh"; then
    fail "dependency direction / boundary violation" "apply the 'fix' from the check-boundaries output above"
  fi
fi

# 2) Pre-commit checks (generated from survey presets: lint, format, type check)
step "pre-commit checks"
if [ -f "$SCRIPT_DIR/pre-commit.sh" ]; then
  bash "$SCRIPT_DIR/pre-commit.sh" || fail "pre-commit checks failed" "run the printed commands and fix the cause"
fi

# 3) Post-commit checks (generated from survey presets: tests, etc.)
step "post-commit checks"
if [ -f "$SCRIPT_DIR/post-commit.sh" ]; then
  bash "$SCRIPT_DIR/post-commit.sh" || fail "post-commit checks failed" "read the failing test output and fix the cause"
fi

echo ""
if [ "$FAILED" -ne 0 ]; then
  echo "[verify] verification FAILED — do the 'next action' above, then re-run."
  exit 1
fi
echo "[verify] all checks passed"
