#!/usr/bin/env bash
# 작업공간에 inbox 레코드 300건을 생성한다. $1 = 작업공간(repo) 경로.
set -euo pipefail
cd "$1"
python3 tools/gen_inbox.py inbox
