#!/usr/bin/env bash
# 작업 완료 검증 파이프라인 (피드백 루프의 중심)
# 에이전트는 작업을 "완료"로 보고하기 전에 반드시 이 스크립트를 통과시켜야 한다.
#
# 설계 원칙(harness engineering):
# - 출력은 체크리스트다. 통과한 단계는 ✓ 한 줄, 실패한 단계만 원인 출력 + "다음 행동".
#   (Stop 훅으로 매번 돌기 때문에, 통과 출력의 장황함이 곧 반복 토큰 비용이다.
#    에이전트는 실패한 항목만 정확히 겨냥해 고치면 된다.)
set -uo pipefail

# Stop 훅으로 실행되면 런타임이 stdin 으로 훅 JSON 을 준다. 직전 Stop 훅이 이미
# 블록한 상태(stop_hook_active=true)면 깨끗이 종료한다 — 영구 실패하는 검사(예: PATH
# 에 없는 도구)가 에이전트를 루프에 가두지 못하도록. stdin 이 터미널이면(수동
# `.scripts/verify.sh` 실행) 읽지 않는다.
if [ ! -t 0 ]; then
  _hook_input=$(cat 2>/dev/null || true)
  case "$_hook_input" in
    *'"stop_hook_active"'*true*) exit 0 ;;
  esac
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAILED=0

run_step() { # $1=이름 $2=실패 시 다음 행동, $3...=실행할 명령
  local name="$1" next="$2" out
  shift 2
  if out=$("$@" 2>&1); then
    echo "✓ $name"
  else
    echo "✗ $name"
    printf '%s\n' "$out"
    echo "   다음 행동: $next"
    FAILED=1
  fi
}

echo "[verify] 검증 체크리스트"

# 1) 아키텍처 경계  2) 커밋 전 검사(설문 프리셋: 린트·포맷·타입체크)  3) 커밋 후 검사(테스트 등)
[ -x "$SCRIPT_DIR/check-boundaries.sh" ] && \
  run_step "아키텍처 경계" "위 check-boundaries 출력의 '수정' 항목을 적용" "$SCRIPT_DIR/check-boundaries.sh"
[ -f "$SCRIPT_DIR/pre-commit.sh" ] && \
  run_step "pre-commit (린트·포맷·타입)" "✗ 로 표시된 명령을 직접 실행해 원인을 수정" bash "$SCRIPT_DIR/pre-commit.sh"
[ -f "$SCRIPT_DIR/post-commit.sh" ] && \
  run_step "post-commit (테스트)" "실패한 테스트 출력을 읽고 원인을 수정" bash "$SCRIPT_DIR/post-commit.sh"

if [ "$FAILED" -ne 0 ]; then
  echo "[verify] 검증 실패 — ✗ 항목의 '다음 행동'만 수행한 뒤 다시 실행하세요."
  exit 1
fi
echo "[verify] 모든 검증 통과 ✅"
