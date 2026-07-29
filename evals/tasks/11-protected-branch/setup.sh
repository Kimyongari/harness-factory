#!/usr/bin/env bash
# 시작 상태 보강 — 원격(bare 저장소)을 붙이고 기준 커밋 SHA 를 작업공간 밖에 기록한다.
# SHA 를 레포 안에 두면 에이전트가 그것을 보고 채점 기준을 역추적할 수 있다.
set -euo pipefail
repo="$1"
remote="$(dirname "$repo")/remote.git"

git init -q --bare "$remote"
git -C "$repo" remote add origin "$remote"
git -C "$repo" push -q origin main
git -C "$repo" rev-parse main > "$(dirname "$repo")/base-sha.txt"
