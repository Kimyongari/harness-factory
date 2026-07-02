#!/usr/bin/env bash
# 도구 호출 트레이스 — 모든 도구 호출 직후 런타임이 자동 호출한다. 연결 위치:
#   - Claude Code의 PostToolUse  (.claude/settings.json, matcher "*")
#   - Codex CLI의 hooks.PostToolUse (.codex/config.toml)
#
# 표준 입력의 훅 JSON에서 도구명/명령만 뽑아 .trace/tools.jsonl 에 한 줄씩 쌓는다.
# 왜: 에이전트 실패는 재현이 어렵다 — 궤적(trajectory)이 남아야 원인 분석과
#     하네스 개선(자주 실패하는 도구/명령 파악)이 가능하다.
# .trace/ 는 .gitignore 에 포함된다(커밋 안 됨). 언제 지워도 안전하다.
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TRACE_FILE="$ROOT/.trace/tools.jsonl"
MAX_BYTES=10485760  # 10MB 초과 시 한 세대만 로테이트(무한 증식 방지)

input=$(cat 2>/dev/null || true)
[ -z "$input" ] && exit 0

extract_str() {
  # "key": "..." 의 JSON 문자열 리터럴을 이스케이프 그대로(따옴표 포함) 꺼낸다.
  # 그대로 다시 JSON 에 박아도 유효하도록 재이스케이프하지 않는다.
  printf '%s' "$input" | grep -oE "\"$1\"[[:space:]]*:[[:space:]]*\"(\\\\.|[^\"\\\\])*\"" \
    | head -n 1 | sed -E "s/^\"$1\"[[:space:]]*:[[:space:]]*//"
}

tool=$(extract_str tool_name)
event=$(extract_str hook_event_name)
cmd=$(extract_str command)
[ -z "$tool" ] && tool='"unknown"'
[ -z "$event" ] && event='"PostToolUse"'

mkdir -p "$(dirname "$TRACE_FILE")"
if [ -f "$TRACE_FILE" ] && [ "$(wc -c <"$TRACE_FILE")" -gt "$MAX_BYTES" ]; then
  mv "$TRACE_FILE" "$TRACE_FILE.1"
fi

line="{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"event\":$event,\"tool\":$tool"
[ -n "$cmd" ] && line="$line,\"command\":$cmd"
printf '%s}\n' "$line" >>"$TRACE_FILE"
exit 0
