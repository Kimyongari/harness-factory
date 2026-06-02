#!/bin/bash
#
# Oracle Cloud (OCI) VM 부팅 시 자동 실행되는 배포 스크립트.
# Compute Instance 생성 화면의 "Advanced options → Management → Cloud-init script"
# (= user_data) 에 이 파일 내용을 그대로 붙여넣으면, 인스턴스 생성과 동시에
# harness-factory 가 빌드/실행됩니다. (대상 OS: Ubuntu 22.04 / 24.04)
#
# 흐름: Docker 설치 → GitHub(main) clone → docker build → 컨테이너 실행(호스트 80 → 컨테이너 8000)
#
set -euxo pipefail

# 모든 출력을 로그 파일로도 남긴다 (디버깅: sudo cat /var/log/harness-init.log)
exec > >(tee -a /var/log/harness-init.log) 2>&1
echo "[harness-init] start $(date -u)"

# ---- 설정값 -------------------------------------------------------------
REPO_URL="https://github.com/Kimyongari/harness-factory.git"
BRANCH="main"
APP_DIR="/opt/harness-factory"
IMAGE="harness-factory:latest"
CONTAINER="harness-factory"
HOST_PORT=80          # 외부 노출 포트
CONTAINER_PORT=8000   # 컨테이너 내부 앱 포트
# ------------------------------------------------------------------------

export DEBIAN_FRONTEND=noninteractive

# cloud-init / unattended-upgrades 가 apt 락을 잡고 있을 수 있으므로 대기
wait_for_apt() {
  for _ in $(seq 1 60); do
    if ! fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 \
       && ! fuser /var/lib/apt/lists/lock  >/dev/null 2>&1; then
      return 0
    fi
    echo "[harness-init] apt 락 대기 중..."
    sleep 5
  done
}

# ---- 1. Docker 설치 (공식 apt 저장소) ----------------------------------
if ! command -v docker >/dev/null 2>&1; then
  wait_for_apt
  apt-get update -y
  apt-get install -y ca-certificates curl git

  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc

  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list

  wait_for_apt
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
systemctl enable --now docker

# ---- 2. 소스 가져오기 (clone 또는 최신화) -------------------------------
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" fetch --depth 1 origin "$BRANCH"
  git -C "$APP_DIR" reset --hard "origin/$BRANCH"
else
  git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

# ---- 3. 이미지 빌드 -----------------------------------------------------
docker build -t "$IMAGE" "$APP_DIR"

# ---- 4. 컨테이너 (재)실행 -----------------------------------------------
docker rm -f "$CONTAINER" 2>/dev/null || true
docker run -d \
  --name "$CONTAINER" \
  --restart unless-stopped \
  -p "${HOST_PORT}:${CONTAINER_PORT}" \
  "$IMAGE"

# ---- 5. 호스트 방화벽: 80 포트 인바운드 허용 ----------------------------
# OCI Ubuntu 이미지는 기본 iptables INPUT 체인에 REJECT 규칙이 있어 막힐 수 있다.
# (Docker 게시 포트는 FORWARD 체인을 타지만, 안전하게 INPUT 도 열어둔다.)
if command -v iptables >/dev/null 2>&1; then
  iptables -C INPUT -p tcp --dport "${HOST_PORT}" -j ACCEPT 2>/dev/null \
    || iptables -I INPUT 1 -p tcp --dport "${HOST_PORT}" -j ACCEPT
  if command -v netfilter-persistent >/dev/null 2>&1; then
    netfilter-persistent save || true
  fi
fi

echo "[harness-init] done $(date -u) — http://<INSTANCE_PUBLIC_IP>/ 로 접속하세요."
