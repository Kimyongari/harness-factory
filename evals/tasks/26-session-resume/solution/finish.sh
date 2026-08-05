#!/usr/bin/env bash
# 골든 마무리 — 이 태스크는 '세션이 끊겨도 살아남는 기억' 을 재므로,
# 정답 상태에는 진행 기록이 파일로 남아 있어야 한다.
set -euo pipefail
cd "$1"
cat > PLAN.md <<'MD'
# 진행 중 작업

## 목표
validators 의 검증 함수 4개에 빈 문자열 입력 처리를 추가한다
→ verify: 빈 문자열에 대해 예외 없이 False 를 돌려준다

## 단계
- [x] email — 빈 문자열 방어 추가
- [x] phone — 빈 문자열 방어 추가
- [x] postal — 빈 문자열 방어 추가
- [x] url — 빈 문자열 방어 추가
MD
