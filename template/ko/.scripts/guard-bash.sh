#!/usr/bin/env bash
# 셸 명령 호출의 결정론적 가드. 연결 위치:
#   - Claude Code PreToolUse       (.claude/settings.json, matcher "Bash")
#   - Codex CLI hooks.PreToolUse   (.codex/config.toml, matcher "Bash")
#   - Cursor beforeShellExecution  (.cursor/hooks.json)
#
# 핵심: raw JSON 을 grep 하지 않는다. 먼저 실행될 "명령 문자열"을 추출·디코드한 뒤
#       디코드된 평문에 위험 패턴을 매칭한다.
#       (예전엔 raw JSON 을 `"command":"[^"]*<패턴>` 로 grep 해서, 따옴표 인자가
#        위험 토큰 앞에 오면 가드가 통째로 뚫렸다 — 예: git commit -m "x" --no-verify.)
# 차단 시 도구 스키마에 맞는 deny 출력을 내고 exit 0. 문제 없으면 조용히 exit 0.
# 규칙을 늘리려면 이 파일을 수정하라. 모델이 런타임을 설득해 끄지 못한다.
set -uo pipefail

NEVER_TOUCH="{{FILL:dev.never_touch}}"

input=$(cat 2>/dev/null || true)

# --- 명령 문자열 추출 + JSON 디코드 -----------------------------------------
# Claude/Codex 는 tool_input.command, Cursor 는 top-level command 에 담는다.
# 둘 다 "command":"..." 형태이므로 동일 추출식이 통한다. 이스케이프(\" \\)는 보존해
# 뽑은 뒤 여기서 해제한다. 콜론 뒤 공백 유무와 무관(직렬화 차이 흡수).
raw=$(printf '%s' "$input" \
  | grep -oE '"command"[[:space:]]*:[[:space:]]*"(\\.|[^"\\])*"' \
  | head -n 1 \
  | sed -E 's/^"command"[[:space:]]*:[[:space:]]*"//; s/"$//')
cmd=$(printf '%s' "$raw" | sed -E 's/\\n/ /g; s/\\t/ /g; s/\\r/ /g; s/\\"/"/g; s/\\\\/\\/g')

# 실행될 명령이 없으면(비-셸 도구 등) 검사할 것이 없다.
[ -z "$cmd" ] && exit 0

# --- deny 출력: 도구별 스키마 분기 -------------------------------------------
# Cursor(beforeShellExecution)는 {"permission":"deny",...}, Claude/Codex 는
# hookSpecificOutput.permissionDecision="deny". 둘 다 exit 0 으로 낸다.
_json_escape() { printf '%s' "$1" | sed -E 's/\\/\\\\/g; s/"/\\"/g'; }
if printf '%s' "$input" | grep -qE '"hook_event_name"[[:space:]]*:[[:space:]]*"beforeShellExecution"'; then
  deny() {
    msg=$(_json_escape "$1")
    printf '{"permission":"deny","agent_message":"%s","user_message":"%s"}\n' "$msg" "$msg"
    exit 0
  }
else
  deny() {
    msg=$(_json_escape "$1")
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$msg"
    exit 0
  }
fi

# 디코드된 명령에 대해서만 매칭한다. B: 명령/경로 경계(따옴표·구분자 뒤도 포함해
# `bash -c "rm -rf …"` 같은 우회를 잡되, 단어 내부 부분일치(charm 의 rm)는 제외).
has() { printf '%s' "$cmd" | grep -qE -- "$1"; }
B='(^|[^[:alnum:]_])'

# 1) 훅 우회 플래그 — 묵시적 허용 금지.
has '(--no-verify)'   && deny "차단: --no-verify 는 커밋 훅을 건너뜁니다. 실패 원인을 고치세요."
has '(--no-gpg-sign)' && deny "차단: --no-gpg-sign. 커밋 서명을 끄려면 사용자에게 확인받으세요."

# 2) 되돌릴 수 없는 기본 명령 — 반드시 명시적 요청 필요.
has "${B}rm[[:space:]]+(-[[:alnum:]]*[rRfF]|--recursive|--force)" \
  && deny "차단: rm -r/-f. 허용되는 대안 — 디렉터리는 find <dir> -type f -delete && rmdir <dir>, 파일은 rm <파일>. (gitignore 된 캐시·산출물에는 git clean 이 -x 없이는 안 통한다 — find/rm 을 쓰라.) 사용자가 이미 삭제/정리를 요청했다면 재확인 없이 진행하고, 끝나면 삭제됐는지 ls 로 확인하라."
has "${B}git[[:space:]]+reset[[:space:]]+--hard" \
  && deny "차단: git reset --hard 는 작업을 버립니다. 허용되는 대안 — git stash (보존) 또는 git switch -c <백업브랜치> 후 되돌리기."
has "${B}git[[:space:]]+checkout[[:space:]]+\\.([[:space:]]|\$)" \
  && deny "차단: git checkout . 는 로컬 변경을 전부 버립니다. 허용되는 대안 — 되돌릴 파일만 git checkout -- <파일>."
has "${B}git[[:space:]]+clean[[:space:]][^|;]*-[[:alnum:]]*[xX]" \
  && deny "차단: git clean -x/-X 는 .env 같은 로컬 시크릿까지 쓸어 갑니다. 허용되는 대안 — 지울 gitignore 산출물만 골라 find <dir> -type f -delete && rmdir <dir> 또는 rm <파일>. (미추적·비무시 파일이라면 git clean -fd <경로>.)"
has "${B}git[[:space:]]+branch[[:space:]][^|;]*(-[[:alnum:]]*D|--delete[[:space:]]+--force)" \
  && deny "차단: git branch -D 는 병합되지 않은 커밋을 버립니다. -d 를 쓰거나 백업 ref 를 먼저 만드세요."

# 2-a) 통째 스테이징 — 시크릿·대용량이 함께 담기는 가장 흔한 경로다.
has "${B}git[[:space:]]+(add|stage)[[:space:]]+(-A|--all|\.)([[:space:]]|\$)" \
  && deny "차단: git add -A/. 는 의도치 않은 파일을 함께 담습니다. 파일을 이름으로 명시하세요."
has "${B}git[[:space:]]+commit[^|;]*[[:space:]]-[^-[:space:]]*a" \
  && deny "차단: git commit -a 는 스테이징을 건너뜁니다. 파일을 이름으로 명시해 add 하세요."

# 2-b) force push — --force / 후치 -f / +refspec 모두 차단(안전한 --force-with-lease 는 허용).
if has "${B}git[[:space:]].*push"; then
  has '(--force([^-]|$)|(^|[[:space:]])-f([[:space:]]|$)|[[:space:]]\+[^[:space:]:]+)' \
    && deny "차단: force push. 사용자에게 명시적으로 확인받으세요. (필요하면 --force-with-lease 를 검토)"
fi

# 2-c) 원격 코드 실행 / 권한 상승 — 기본 차단(명시 요청 시에만).
has '\|[[:space:]]*(sudo[[:space:]]+)?(ba)?sh([[:space:]]|;|&|$)' \
  && deny "차단: 파이프-투-셸(예: curl … | sh)은 검증 없이 원격 코드를 실행합니다."
has "${B}sudo[[:space:]]" \
  && deny "차단: sudo 권한 상승. 정말 필요하면 사용자에게 확인받으세요."
has "${B}chmod[[:space:]]+([^[:space:]]+[[:space:]]+)*(0?777|a\\+rwx)" \
  && deny "차단: chmod 777/a+rwx 는 과도한 권한 부여입니다."

# 3) 설문의 보호 경로(dev.never_touch)에 대한 쓰기/이동/삭제/스테이징 차단.
IFS=',' read -ra PATHS <<<"$NEVER_TOUCH"
for rawp in "${PATHS[@]:-}"; do
  p=$(printf '%s' "$rawp" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
  [ -z "$p" ] && continue
  esc=$(printf '%s' "$p" | sed -E 's/[][\\.^$*+?(){}|/]/\\&/g')
  has "${B}(rm|mv|cp|tee|chmod|chown|sed|truncate|dd|install)[[:space:]]+([^[:space:]]+[[:space:]]+)*${esc}" \
    && deny "차단: '${p}' 은(는) never_touch 경로입니다."
  has ">[[:space:]]*${esc}" \
    && deny "차단: '${p}' (never_touch) 로 출력 리디렉션."
  has "${B}git[[:space:]]+(add|stage)[[:space:]][^|]*${esc}" \
    && deny "차단: never_touch 경로 '${p}' 를 git 스테이징하려 합니다(시크릿 커밋 방지)."
done

exit 0
