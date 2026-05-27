#!/usr/bin/env bash
# 아키텍처 경계 기계적 강제 (Mechanical Enforcement)
# 규칙 정의: .docs/design/architecture.md
#
# 핵심: 위반 시 단순 실패가 아니라, 에이전트가 읽고 "스스로 고칠 수 있는"
#       에러 메시지를 출력한다 (무엇을/어디서/왜/어떻게).
set -uo pipefail

VIOLATIONS=0

emit_violation() {
  # $1=규칙  $2=위치  $3=이유  $4=수정법
  echo "❌ 경계 위반: $1"
  echo "   위치 : $2"
  echo "   이유 : $3"
  echo "   수정 : $4"
  echo ""
  VIOLATIONS=$((VIOLATIONS + 1))
}

echo "[check-boundaries] 의존성 방향 검사 시작..."
echo "  허용 방향: Types → Config → Repo → Service → Runtime → UI"
echo ""

# --- 예시 규칙: 하위 레이어가 UI를 import하면 위반 ---
# 프로젝트 스택에 맞게 grep 패턴/레이어 경로를 수정하세요.
#
# if grep -rn "import .*\.ui" src/service 2>/dev/null | grep -q .; then
#   emit_violation \
#     "Service → UI 역방향 의존" \
#     "$(grep -rn 'import .*\.ui' src/service)" \
#     "Service는 UI를 알 수 없다 (의존성은 한 방향)" \
#     "UI 의존을 제거하거나, 필요한 데이터를 인터페이스/포트로 주입받도록 변경"
# fi

if [ "$VIOLATIONS" -gt 0 ]; then
  echo "[check-boundaries] 위반 ${VIOLATIONS}건. 위 메시지의 '수정'을 적용한 뒤 다시 실행하세요."
  exit 1
fi

echo "[check-boundaries] 경계 통과 ✅"
