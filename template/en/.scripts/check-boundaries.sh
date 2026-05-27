#!/usr/bin/env bash
# Mechanical enforcement of architecture boundaries.
# Rules defined in: .docs/design/architecture.md
#
# Key: on violation, don't just fail — print an agent-readable message it can
#      self-correct from (what / where / why / how to fix).
set -uo pipefail

VIOLATIONS=0

emit_violation() {
  # $1=rule  $2=location  $3=reason  $4=fix
  echo "VIOLATION: $1"
  echo "   where: $2"
  echo "   why  : $3"
  echo "   fix  : $4"
  echo ""
  VIOLATIONS=$((VIOLATIONS + 1))
}

echo "[check-boundaries] checking dependency direction..."
echo "  allowed: {{FILL:dev.architecture_layers}}"
echo ""

# --- Example rule: a lower layer importing the UI is a violation ---
# Adjust grep patterns / layer paths to your stack.
#
# if grep -rn "import .*\.ui" src/service 2>/dev/null | grep -q .; then
#   emit_violation \
#     "Service -> UI reverse dependency" \
#     "$(grep -rn 'import .*\.ui' src/service)" \
#     "Service must not know UI (dependencies are one-way)" \
#     "remove the UI import, or inject needed data via an interface/port"
# fi

if [ "$VIOLATIONS" -gt 0 ]; then
  echo "[check-boundaries] ${VIOLATIONS} violation(s). Apply the 'fix' above and re-run."
  exit 1
fi

echo "[check-boundaries] boundaries OK"
