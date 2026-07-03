#!/usr/bin/env bash
# 세션 시작 컨텍스트 주입 — 런타임이 세션 시작/재개/clear/압축 후 자동 호출한다.
#   - Claude Code SessionStart (.claude/settings.json)
#   - Codex CLI hooks.SessionStart (.codex/config.toml)
#
# 왜: 긴 세션은 컨텍스트가 유실되고(특히 자동 압축 후) 에이전트가 진행 중 작업과
#     현재 상태를 잊는다. 세션이 시작될 때마다 진행 상태 포인터를 다시 주입한다.
# 출력(stdout)은 이 이벤트에서 컨텍스트로 그대로 주입되므로 JSON 없이 평문으로 낸다.
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

echo "## 세션 컨텍스트 (자동 주입)"
if git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  branch=$(git -C "$ROOT" branch --show-current 2>/dev/null)
  echo "- 브랜치: ${branch:-(detached)}"
  changed=$(git -C "$ROOT" status --short 2>/dev/null | head -n 20)
  if [ -n "$changed" ]; then
    echo "- 미커밋 변경:"
    printf '%s\n' "$changed" | sed 's/^/    /'
  else
    echo "- 미커밋 변경: 없음"
  fi
fi
[ -f "$ROOT/PLAN.md" ] && echo "- 진행 중 작업은 PLAN.md 를 읽어 이어간다(자동 압축은 손실이 있으니 상태는 PLAN.md 기준)."
echo "- 무슨 문서가 필요한지 모르면 .docs/index.md 로 라우팅한다(필요할 때만 읽기, just-in-time)."
exit 0
