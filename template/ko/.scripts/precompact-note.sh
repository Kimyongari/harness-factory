#!/usr/bin/env bash
# 압축 직전 알림 — 런타임이 컨텍스트 자동/수동 압축 직전에 호출한다.
#   - Claude Code PreCompact (.claude/settings.json)
#   - Codex CLI hooks.PreCompact (.codex/config.toml)
#
# 왜: 압축은 손실이 있다. 핵심 결정/미해결 이슈가 컨텍스트에만 있으면 사라진다.
#     압축 전에 "PLAN.md 에 상태를 남겼는지" 상기시킨다. (블록하지 않는다 — 알림만.)
set -uo pipefail
echo "[precompact] 컨텍스트가 곧 압축됩니다(손실 있음). 핵심 결정·미해결 이슈·다음 단계가 PLAN.md 에 남아있는지 확인하세요. 압축 후에는 SessionStart 가 PLAN.md 포인터를 다시 주입합니다."
exit 0
