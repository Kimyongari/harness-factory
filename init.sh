#!/bin/bash
#
# Oracle Cloud (OCI) VM 부팅 시 자동 실행되는 배포 스크립트.
# Compute Instance 생성 화면의 "Advanced options → Management → Cloud-init script"
# (= user_data) 에 이 파일 내용을 그대로 붙여넣으면, 인스턴스 생성과 동시에
# harness-factory 가 빌드/실행됩니다. (대상 OS: Oracle Linux 8 / 9)
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

# ---- 1. Docker 설치 (Docker 공식 CentOS/RHEL 저장소 사용) ---------------
if ! command -v docker >/dev/null 2>&1; then
  dnf install -y dnf-plugins-core git
  dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

  # containerd.io 가 Oracle Linux 기본 runc/podman 과 충돌할 수 있어 --allowerasing 사용
  dnf install -y --allowerasing \
    docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
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
# Oracle Linux 이미지는 firewalld 또는 iptables 로 인바운드를 막아둔다.
# 둘 다 안전하게 처리한다.
if systemctl is-active --quiet firewalld; then
  # firewalld 가 동작 중인 경우
  firewall-cmd --permanent --add-port="${HOST_PORT}/tcp"
  firewall-cmd --reload
else
  # 레거시 iptables(OCI Oracle Linux 기본) 경우
  if command -v iptables >/dev/null 2>&1; then
    iptables -C INPUT -p tcp --dport "${HOST_PORT}" -j ACCEPT 2>/dev/null \
      || iptables -I INPUT 1 -p tcp --dport "${HOST_PORT}" -j ACCEPT
    # 재부팅 후에도 유지되도록 저장
    if command -v netfilter-persistent >/dev/null 2>&1; then
      netfilter-persistent save || true
    else
      iptables-save > /etc/sysconfig/iptables || true
    fi
  fi
fi

echo "[harness-init] done $(date -u) — http://<INSTANCE_PUBLIC_IP>/ 로 접속하세요."
