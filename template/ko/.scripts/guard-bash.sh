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

NEVER_TOUCH="{{FILL:dev.never_touch}}"
PROTECTED_BRANCH="{{FILL:gh.default_branch}}"

input=$(cat 2>/dev/null || true)

deny() {
  # Claude Code / Codex hooks 레퍼런스의 JSON 형식.
  cat <<EOF
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"$1"}}
EOF
  exit 0
}

contains() { printf '%s' "$input" | grep -qE "$1"; }

# Claude Code / Codex 모두 명령 문자열을 tool_input.command 에 담아 단일 JSON 으로 stdin 에 준다.
# 직렬화가 콜론 뒤 공백을 넣든 안 넣든("command"[[:space:]]*:[[:space:]]*"x" / "command": "x") 동일하게 잡도록
# 아래 정규식들은 공백을 허용한다. (공백 미허용 시 가드가 조용히 통과하는 silent failure 발생.)

# 1) 훅 우회 플래그 — 묵시적 허용 금지.
contains '"command"[[:space:]]*:[[:space:]]*"[^"]*--no-verify'       && deny "차단: --no-verify 는 커밋 훅을 건너뜁니다. 실패 원인을 고치세요."
contains '"command"[[:space:]]*:[[:space:]]*"[^"]*--no-gpg-sign'     && deny "차단: --no-gpg-sign. 커밋 서명을 끄려면 사용자에게 명시적으로 확인받으세요."

# 2) 되돌릴 수 없는 기본 명령 — 반드시 명시적 요청 필요.
contains '"command"[[:space:]]*:[[:space:]]*"[^"]*\brm[[:space:]]+-[rRfF]+\b' && deny "차단: rm -rf. 더 좁은 삭제로 바꾸거나 사용자 확인을 받으세요."
contains '"command"[[:space:]]*:[[:space:]]*"[^"]*\bgit[[:space:]]+push[[:space:]]+(--force|-f[[:space:]])' && deny "차단: force push. 사용자에게 명시적으로 확인받으세요."
contains '"command"[[:space:]]*:[[:space:]]*"[^"]*\bgit[[:space:]]+reset[[:space:]]+--hard'                && deny "차단: git reset --hard 는 작업을 버립니다. 먼저 stash 또는 새 브랜치로."
contains '"command"[[:space:]]*:[[:space:]]*"[^"]*\bgit[[:space:]]+checkout[[:space:]]+\.[[:space:]]*\\?"'  && deny "차단: git checkout . 는 로컬 변경을 버립니다."

# 2-b) 원격 코드 실행 / 권한 상승 — 기본 차단(명시 요청 시에만).
contains '"command":"[^"]*\|[[:space:]]*(sudo[[:space:]]+)?(ba)?sh\b' && deny "차단: 파이프-투-셸(예: curl … | sh)은 검증 없이 원격 코드를 실행합니다."
contains '"command":"[^"]*\bsudo[[:space:]]'                         && deny "차단: sudo 권한 상승. 정말 필요하면 사용자에게 확인받으세요."
contains '"command":"[^"]*\bchmod[[:space:]]+([^"]*[[:space:]])?(0?777|a\+rwx)\b' && deny "차단: chmod 777/a+rwx 는 과도한 권한 부여입니다."

# 3) 보호 브랜치에 force push — 항상 거부.
if [ -n "$PROTECTED_BRANCH" ]; then
  contains "\"command\"[[:space:]]*:[[:space:]]*\"[^\"]*\\bgit[[:space:]]+push[[:space:]]+[^\"]*${PROTECTED_BRANCH}\\b[^\"]*(--force|-f[[:space:]])" \
    && deny "차단: 보호 브랜치 '$PROTECTED_BRANCH' 에 --force 푸시."
fi

# 4) 설문의 보호 경로(dev.never_touch)에 대한 쓰기/이동/삭제 차단.
IFS=',' read -ra PATHS <<<"$NEVER_TOUCH"
for raw in "${PATHS[@]:-}"; do
  p=$(printf '%s' "$raw" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
  [ -z "$p" ] && continue
  esc=$(printf '%s' "$p" | sed -E 's/[][\\.^$*+?(){}|/]/\\&/g')
  contains "\"command\"[[:space:]]*:[[:space:]]*\"[^\"]*\\b(rm|mv|cp|tee|chmod|chown)\\b[^\"]*${esc}" \
    && deny "차단: '${p}' 은(는) never_touch 경로입니다."
  contains "\"command\"[[:space:]]*:[[:space:]]*\"[^\"]*>[[:space:]]*${esc}" \
    && deny "차단: '${p}' (never_touch) 로 출력 리디렉션."
  contains "\"command\":\"[^\"]*\\bgit[[:space:]]+(add|stage)\\b[^\"]*${esc}" \
    && deny "차단: never_touch 경로 '${p}' 를 git 스테이징하려 합니다(시크릿 커밋 방지)."
done

exit 0
