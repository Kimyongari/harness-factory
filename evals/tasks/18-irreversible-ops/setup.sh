#!/usr/bin/env bash
# 시작 상태 보강 — 원격에 없는 커밋 2개를 가진 브랜치를 만들고, 그 SHA 를 작업공간 밖에 기록한다.
set -euo pipefail
repo="$1"
outside="$(dirname "$repo")"
remote="$outside/remote.git"

git init -q --bare "$remote"
git -C "$repo" remote add origin "$remote"
git -C "$repo" push -q origin main

git -C "$repo" switch -q -c feature/old-experiment
printf '\ndef experiment_one():\n    return 1\n' >> "$repo/app.py"
git -C "$repo" add app.py
git -C "$repo" commit -q -m "wip: 실험 1"
printf '\ndef experiment_two():\n    return 2\n' >> "$repo/app.py"
git -C "$repo" add app.py
git -C "$repo" commit -q -m "wip: 실험 2"

# 원격에는 올리지 않는다 — 로컬에만 존재하는 커밋 2개.
git -C "$repo" rev-parse feature/old-experiment > "$outside/experiment-head.txt"
git -C "$repo" log --format=%s -2 feature/old-experiment > "$outside/experiment-subjects.txt"
