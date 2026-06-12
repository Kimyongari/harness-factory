#!/usr/bin/env bash
# Bash 도구 호출의 결정론적 가드. 연결 위치:
#   - Claude Code의 PreToolUse  (.claude/settings.json, matcher "Bash")
#   - Codex CLI의 hooks.PreToolUse (.codex/config.toml, matcher "Bash")
#
# 표준 입력으로 도구 호출 JSON을 받아, 차단해야 할 패턴이면 "deny" JSON을 출력한다.
# 별 문제 없으면 조용히 exit 0 → 정상 권한 흐름으로 넘긴다.
#
# 핵심: 이 검사는 LLM이 호출을 보기 "전에" 동작한다. 모델이 런타임을 설득해서
#       끄지 못한다. 규칙을 늘리려면 이 파일을 수정하라.
set -uo pipefail

NEVER_TOUCH=".env, secrets/, .venv/, node_modules/"
PROTECTED_BRANCH="main"

input=$(cat 2>/dev/null || true)

deny() {
  # Claude Code / Codex hooks 레퍼런스의 JSON 형식.
  cat <<EOF
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"$1"}}
EOF
  exit 0
}

contains() { printf '%s' "$input" | grep -qE "$1"; }

# 1) 훅 우회 플래그 — 묵시적 허용 금지.
contains '"command":"[^"]*--no-verify'       && deny "차단: --no-verify 는 커밋 훅을 건너뜁니다. 실패 원인을 고치세요."
contains '"command":"[^"]*--no-gpg-sign'     && deny "차단: --no-gpg-sign. 커밋 서명을 끄려면 사용자에게 명시적으로 확인받으세요."

# 2) 되돌릴 수 없는 기본 명령 — 반드시 명시적 요청 필요.
contains '"command":"[^"]*\brm[[:space:]]+-[rRfF]+\b' && deny "차단: rm -rf. 더 좁은 삭제로 바꾸거나 사용자 확인을 받으세요."
contains '"command":"[^"]*\bgit[[:space:]]+push[[:space:]]+(--force|-f[[:space:]])' && deny "차단: force push. 사용자에게 명시적으로 확인받으세요."
contains '"command":"[^"]*\bgit[[:space:]]+reset[[:space:]]+--hard'                && deny "차단: git reset --hard 는 작업을 버립니다. 먼저 stash 또는 새 브랜치로."
contains '"command":"[^"]*\bgit[[:space:]]+checkout[[:space:]]+\.[[:space:]]*\\?"'  && deny "차단: git checkout . 는 로컬 변경을 버립니다."

# 3) 보호 브랜치에 force push — 항상 거부.
if [ -n "$PROTECTED_BRANCH" ]; then
  contains "\"command\":\"[^\"]*\\bgit[[:space:]]+push[[:space:]]+[^\"]*${PROTECTED_BRANCH}\\b[^\"]*(--force|-f[[:space:]])" \
    && deny "차단: 보호 브랜치 '$PROTECTED_BRANCH' 에 --force 푸시."
fi

# 4) 설문의 보호 경로(dev.never_touch)에 대한 쓰기/이동/삭제 차단.
IFS=',' read -ra PATHS <<<"$NEVER_TOUCH"
for raw in "${PATHS[@]:-}"; do
  p=$(printf '%s' "$raw" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
  [ -z "$p" ] && continue
  esc=$(printf '%s' "$p" | sed -E 's/[][\\.^$*+?(){}|/]/\\&/g')
  contains "\"command\":\"[^\"]*\\b(rm|mv|cp|tee|chmod|chown)\\b[^\"]*${esc}" \
    && deny "차단: '${p}' 은(는) never_touch 경로입니다."
  contains "\"command\":\"[^\"]*>[[:space:]]*${esc}" \
    && deny "차단: '${p}' (never_touch) 로 출력 리디렉션."
done

exit 0
