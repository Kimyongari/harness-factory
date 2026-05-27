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

# 2) Tests (adjust to your stack)
step "tests"
if command -v pytest >/dev/null 2>&1; then
  pytest || fail "tests failed" "read the failing assertion messages and fix the cause"
elif [ -f package.json ]; then
  npm test || fail "tests failed" "read the failing test output and fix the cause"
else
  fail "no test runner" "set verification.test_cmd in .agents/agent.yaml"
fi

echo ""
if [ "$FAILED" -ne 0 ]; then
  echo "[verify] verification FAILED — do the 'next action' above, then re-run."
  exit 1
fi
echo "[verify] all checks passed"
