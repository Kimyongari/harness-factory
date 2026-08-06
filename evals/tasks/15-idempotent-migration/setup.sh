#!/usr/bin/env bash
# 작업공간에 초기 DB 를 만든다. $1 = 작업공간(repo) 경로.
set -euo pipefail
cd "$1"
python3 db/init_db.py app.db
