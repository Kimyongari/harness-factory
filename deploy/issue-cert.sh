#!/usr/bin/env bash
# Let's Encrypt 인증서를 발급하고 자동 갱신 타이머를 건다. **서버에서 한 번만** 실행한다.
#
#   ssh <user>@<host> 'sudo bash -s' -- [알림받을 이메일] < deploy/issue-cert.sh
#
# 실행하면 Let's Encrypt 가입 약관(Subscriber Agreement)에 동의하게 된다. 그래서 CI 가 매 배포마다
# 돌리지 않고, 사람이 약관을 읽고 직접 실행한다. 이메일을 주면 만료 알림을 받고, 생략하면 이메일 없이
# 등록한다(갱신은 아래 타이머가 하므로 알림 없이도 돈다).
#
# 순서 (README 의 HTTPS 절과 같다):
#   1) 이 변경이 배포되어 프록시가 /.well-known/acme-challenge/ 를 ACME_ROOT 에서 서빙하고 있을 것
#   2) 443 개방: ssh <user>@<host> 'sudo bash -s' -- 443 < deploy/open-http-port.sh
#   3) 이 스크립트 실행
#   4) 재배포(GitHub Actions 에서 마지막 deploy 를 Re-run). 배포가 인증서를 찾아 443 설정을 켠다
set -euo pipefail

EMAIL="${1:-}"
DOMAIN=harness-factory.kr
ACME_ROOT=/var/www/certbot
CERTBOT_IMAGE=certbot/certbot:v2.11.0
PROXY=harness-factory-proxy

if [ "$(id -u)" -ne 0 ]; then
    echo "root 로 실행해야 한다: sudo bash $0 [email]" >&2
    exit 1
fi
DOCKER="$(command -v docker)"
if [ -n "${EMAIL}" ]; then
    ACCOUNT=(-m "${EMAIL}" --no-eff-email)
else
    ACCOUNT=(--register-unsafely-without-email)
fi

echo "== 1) 인증 경로 확인 =="
# 인증 서버는 80 으로 토큰을 읽는다. 프록시가 이 경로를 아직 서빙하지 않으면(이 변경이 배포 전이면)
# certbot 이 모호한 오류로 실패하므로, 먼저 직접 확인한다.
mkdir -p "${ACME_ROOT}/.well-known/acme-challenge"
probe="probe-$$"
echo ok > "${ACME_ROOT}/.well-known/acme-challenge/${probe}"
if ! curl -fsS "http://127.0.0.1/.well-known/acme-challenge/${probe}" >/dev/null; then
    rm -f "${ACME_ROOT}/.well-known/acme-challenge/${probe}"
    echo "프록시가 ${ACME_ROOT} 를 서빙하지 않는다. HTTPS 준비 변경을 먼저 배포하라." >&2
    exit 1
fi
rm -f "${ACME_ROOT}/.well-known/acme-challenge/${probe}"
echo "통과"

echo "== 2) 인증서 발급 (${DOMAIN}) =="
"${DOCKER}" run --rm \
    -v /etc/letsencrypt:/etc/letsencrypt \
    -v "${ACME_ROOT}:${ACME_ROOT}" \
    "${CERTBOT_IMAGE}" certonly --webroot -w "${ACME_ROOT}" \
    -d "${DOMAIN}" "${ACCOUNT[@]}" --agree-tos --non-interactive

echo "== 3) 자동 갱신 타이머 (하루 두 번) =="
# 인증서는 90일짜리라 갱신이 멈추면 사이트가 조용히 깨진다. 갱신 뒤 nginx 를 리로드해야 새 인증서를 읽는다.
cat > /etc/systemd/system/harness-factory-certbot.service <<EOF
[Unit]
Description=Renew the harness-factory TLS certificate

[Service]
Type=oneshot
ExecStart=${DOCKER} run --rm -v /etc/letsencrypt:/etc/letsencrypt -v ${ACME_ROOT}:${ACME_ROOT} ${CERTBOT_IMAGE} renew --webroot -w ${ACME_ROOT} --quiet
ExecStartPost=${DOCKER} exec ${PROXY} nginx -s reload
EOF
cat > /etc/systemd/system/harness-factory-certbot.timer <<'EOF'
[Unit]
Description=Twice-daily renewal check for the harness-factory TLS certificate

[Timer]
OnCalendar=*-*-* 03,15:00:00
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now harness-factory-certbot.timer
systemctl list-timers harness-factory-certbot.timer --no-pager

echo
echo "발급 완료. 이제 재배포하면 배포가 인증서를 찾아 443 을 켠다."
echo "확인: curl -fsS -o /dev/null -w '%{http_code}\\n' https://${DOMAIN}/"
