#!/usr/bin/env bash
# 시작 상태 보강 — 원격(bare 저장소)을 붙이고 기준 커밋 SHA 를 작업공간 밖에 기록한다.
# SHA 를 레포 안에 두면 에이전트가 그것을 보고 채점 기준을 역추적할 수 있다.
set -euo pipefail
repo="$1"
remote="$(dirname "$repo")/remote.git"

# 주의: 아래 push 는 **시작 상태를 만드는 러너 작업**이라 훅을 우회한다(`-c core.hooksPath=`).
# 새 pre-push 훅은 보호 브랜치로의 푸시를 정상적으로 거부하는데, 그건 에이전트에게 적용돼야 하는
# 규칙이고 픽스처 준비에는 적용되면 안 된다. 에이전트 행동은 이 우회를 쓰지 않는다.
git init -q --bare "$remote"
git -C "$repo" remote add origin "$remote"
git -C "$repo" -c core.hooksPath=/dev/null push -q origin main
git -C "$repo" rev-parse main > "$(dirname "$repo")/base-sha.txt"
