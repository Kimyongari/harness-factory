#!/usr/bin/env bash
# 인스턴스 방화벽에서 80/tcp 를 연다. **서버에서 한 번만** 실행한다.
#
#   ssh <user>@<host> 'sudo bash -s' < deploy/open-http-port.sh
#
# 왜 배포 스크립트에 넣지 않았나: 방화벽 포트를 여는 것은 보안 경계를 바꾸는 일이라
# CI 가 매 배포마다 조용히 실행할 일이 아니다. 한 번, 사람이, 의도해서 실행한다.
#
# ⚠️ 이 스크립트만으로는 부족하다. OCI 는 방화벽이 두 겹이다:
#   ① 클라우드 쪽 — VCN **보안 목록/NSG** 인그레스 규칙 (OCI 콘솔에서만 가능)
#   ② 인스턴스 쪽 — 아래에서 여는 iptables / firewalld
# ①을 열지 않으면 ②만 열어도 외부에서 접속되지 않는다(연결 거부가 아니라 **타임아웃**으로 보인다).
#
# ① 방법: OCI 콘솔 → Networking → Virtual Cloud Networks → 해당 VCN → Security Lists
#          → Default Security List → Add Ingress Rules
#          Source CIDR `0.0.0.0/0` · IP Protocol `TCP` · Destination Port Range `80`
set -euo pipefail

PORT="${1:-80}"

if [ "$(id -u)" -ne 0 ]; then
    echo "root 로 실행해야 한다: sudo bash $0 $PORT" >&2
    exit 1
fi

echo "== ${PORT}/tcp 개방 =="

if command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
    # Oracle Linux 계열 기본값
    echo "firewalld 감지"
    firewall-cmd --permanent --add-port="${PORT}/tcp"
    firewall-cmd --reload
    firewall-cmd --list-ports

elif command -v iptables >/dev/null 2>&1; then
    # Ubuntu OCI 이미지는 22 를 제외한 인바운드를 REJECT 하는 iptables 규칙을 들고 나온다.
    echo "iptables 감지"
    if iptables -C INPUT -p tcp --dport "${PORT}" -j ACCEPT 2>/dev/null; then
        echo "이미 허용되어 있다 — 건너뜀"
    else
        # REJECT 규칙보다 **앞에** 넣어야 한다. 뒤에 넣으면 도달하지 못한다.
        reject_line="$(iptables -L INPUT --line-numbers -n | awk '/REJECT/ {print $1; exit}')"
        if [ -n "${reject_line:-}" ]; then
            iptables -I INPUT "${reject_line}" -p tcp --dport "${PORT}" -j ACCEPT
        else
            iptables -A INPUT -p tcp --dport "${PORT}" -j ACCEPT
        fi
    fi
    if command -v netfilter-persistent >/dev/null 2>&1; then
        netfilter-persistent save
    elif [ -d /etc/iptables ]; then
        iptables-save > /etc/iptables/rules.v4
    else
        echo "⚠️ 규칙을 영구 저장할 수단을 찾지 못했다 — 재부팅 후 사라질 수 있다." >&2
    fi
    iptables -L INPUT -n --line-numbers | head -12

else
    echo "⚠️ firewalld·iptables 를 찾지 못했다. 호스트 방화벽 설정을 직접 확인하라." >&2
    exit 1
fi

echo
echo "== 확인 =="
echo "서버 안:  curl -fsS -o /dev/null -w '%{http_code}\\n' http://localhost/"
echo "서버 밖:  curl -fsS -o /dev/null -w '%{http_code}\\n' http://harness-factory.kr/"
echo
echo "밖에서 타임아웃이 나면 ① OCI 보안 목록 인그레스 규칙이 아직 없는 것이다(위 주석 참고)."
