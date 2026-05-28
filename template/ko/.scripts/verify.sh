#!/usr/bin/env bash
# 작업 완료 검증 파이프라인 (피드백 루프의 중심)
# 에이전트는 작업을 "완료"로 보고하기 전에 반드시 이 스크립트를 통과시켜야 한다.
#
# 설계 원칙(harness engineering):
# - 각 단계 실패 시 "통과/실패"만이 아니라 원인과 다음 행동을 함께 출력한다.
# - 그래야 에이전트가 사람 개입 없이 스스로 고칠 수 있다.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAILED=0

step() { echo ""; echo "── $1 ──"; }
fail() { echo "❌ $1"; echo "   다음 행동: $2"; FAILED=1; }

echo "[verify] 검증 파이프라인 시작..."

# 1) 아키텍처 경계
step "아키텍처 경계 검사"
if [ -x "$SCRIPT_DIR/check-boundaries.sh" ]; then
  if ! "$SCRIPT_DIR/check-boundaries.sh"; then
    fail "의존성 방향/경계 위반" "위 check-boundaries 출력의 '수정' 항목을 적용"
  fi
fi

# 2) 커밋 전 검사 (설문 프리셋으로 생성됨: 린트·포맷·타입체크)
step "pre-commit 검사"
if [ -f "$SCRIPT_DIR/pre-commit.sh" ]; then
  bash "$SCRIPT_DIR/pre-commit.sh" || fail "pre-commit 검사 실패" "위 출력의 명령을 직접 실행해 원인을 수정"
fi

# 3) 커밋 후 검사 (설문 프리셋으로 생성됨: 테스트 등)
step "post-commit 검사"
if [ -f "$SCRIPT_DIR/post-commit.sh" ]; then
  bash "$SCRIPT_DIR/post-commit.sh" || fail "post-commit 검사 실패" "실패한 테스트 출력을 읽고 원인을 수정"
fi

echo ""
if [ "$FAILED" -ne 0 ]; then
  echo "[verify] 검증 실패 — 위 '다음 행동'을 수행한 뒤 다시 실행하세요."
  exit 1
fi
echo "[verify] 모든 검증 통과 ✅"
