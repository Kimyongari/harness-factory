#!/usr/bin/env bash
# 서버에서 도는 배포 본체. CI 는 이 스크립트를 **분리 실행(setsid)** 하고 결과 파일만 폴링한다.
#
#   bash deploy/remote-deploy.sh <sha> <actor> <run_url>
#
# 왜 분리 실행하나:
#   SSH 채널 안에서 배포를 돌리면 채널이 끊기는 순간 배포가 중단된다. 실제로 그 일이 두 번
#   일어났다 — 앱 컨테이너 재기동 직후 세션이 죽어(출력·종료 트랩 모두 없이) 프록시 단계가
#   실행되지 않았다. OOM 도 sshd 오류도 없었고 원인을 특정하지 못했다.
#   배포를 세션에서 떼어내면 원인이 무엇이든 배포는 끝까지 진행되고, 로그가 남는다.
#
# 산출물 (deploy-logs/):
#   history.log            실행당 한 줄 요약 — 계속 누적
#   <시각>-<sha>.log       실행별 상세 (최근 30개 보관)
#   last-status            CI 폴링용: "SUCCESS" 또는 "FAILURE(rc=N) step=<단계>"
set -uo pipefail

SHA="${1:?sha 인자가 필요하다}"
ACTOR="${2:-unknown}"
RUN_URL="${3:--}"

APP=harness-factory          # 운영 컨테이너
CANARY="${APP}-canary"       # 검증용 임시 컨테이너
PROXY="${APP}-proxy"         # 80 → 8000 리버스 프록시
PORT=8000                    # 앱 포트 — **루프백에만** 바인딩한다(아래 BIND 참고)
CANARY_PORT=8001             # 헬스체크용 임시 포트(서버 내부 전용)
# 앱을 127.0.0.1 에만 공개한다. 외부에서 닿는 경로는 프록시(80) 하나뿐이 된다.
# `-p 8000:8000` 이면 0.0.0.0 에 붙어 `:8000` 으로도 사이트가 열린다 — 공개 URL 이 둘이 되고,
# 프록시를 우회하므로 프록시에 붙인 정책(본문 한도·타임아웃·헤더)이 적용되지 않는다.
# 프록시는 `--network host` 라 호스트의 127.0.0.1:${PORT} 로 앱에 닿는다.
BIND=127.0.0.1
SHORT_SHA="$(printf '%.7s' "${SHA}")"

cd "$(dirname "$0")/.."      # 레포 루트
REPO_ROOT="$(pwd)"
LOG_DIR="${REPO_ROOT}/deploy-logs"
mkdir -p "${LOG_DIR}"

STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
STARTED_EPOCH="$(date +%s)"
RUN_LOG="${LOG_DIR}/${STARTED_AT//:/-}-${SHORT_SHA}.log"
HISTORY="${LOG_DIR}/history.log"
STATUS_FILE="${LOG_DIR}/last-status"
STEP=init                    # 실패 시 "어디서" 죽었는지 남기는 마커

# 이 시점 이후의 모든 출력(표준출력·표준에러)을 상세 로그와 콘솔에 함께 남긴다.
# 원인 불명의 실패를 다시 만나지 않으려면 무엇도 조용히 사라지지 않아야 한다.
exec > >(tee -a "${RUN_LOG}") 2>&1

log() { printf '%s [%s] %s\n' "$(date -u +%H:%M:%S)" "${STEP}" "$*"; }

fail_hard() {
    STEP="$1"
    log "실패: $2"
    exit "${3:-1}"
}

summarize() {
    rc=$?
    elapsed=$(( $(date +%s) - STARTED_EPOCH ))
    if [ "${rc}" -eq 0 ]; then
        result=SUCCESS
    else
        result="FAILURE(rc=${rc})"
    fi
    printf '%s  %-7s  %-16s  step=%-10s  %4ds  %s  %s\n' \
        "${STARTED_AT}" "${SHORT_SHA}" "${result}" "${STEP}" "${elapsed}" "${ACTOR}" "${RUN_URL}" \
        >> "${HISTORY}"
    printf '%s step=%s elapsed=%ss\n' "${result}" "${STEP}" "${elapsed}" > "${STATUS_FILE}"
    log "종료 ${result} (${elapsed}s)"
    # 실행별 로그는 최근 30개만 남긴다(요약 history.log 는 계속 누적).
    find "${LOG_DIR}" -maxdepth 1 -name '*-*.log' -printf '%T@ %p\n' 2>/dev/null \
        | sort -rn | tail -n +31 | cut -d' ' -f2- | xargs -r rm -f || true
}
trap summarize EXIT

log "배포 시작 sha=${SHA} actor=${ACTOR}"

# ── 1) 이미지 빌드. 실패하면 운영 컨테이너를 손대지 않았으므로 사이트는 그대로다.
STEP=build
log "이미지 빌드"
sudo docker build -t "${APP}:${SHA}" -t "${APP}:latest" . \
    || fail_hard build "docker build 실패"

# ── 2) 카나리를 임시 포트로 띄워 헬스체크(운영 컨테이너는 계속 ${PORT} 에서 서비스 중).
STEP=canary
log "카나리 기동 (포트 ${CANARY_PORT})"
sudo docker rm -f "${CANARY}" >/dev/null 2>&1 || true
sudo docker run -d --name "${CANARY}" -p "${BIND}:${CANARY_PORT}:8000" "${APP}:${SHA}" \
    || fail_hard canary "카나리 기동 실패"

ok=0
for _ in $(seq 1 20); do
    if curl -fsS "http://localhost:${CANARY_PORT}/" >/dev/null 2>&1; then ok=1; break; fi
    sleep 2
done
if [ "${ok}" != "1" ]; then
    STEP=canary
    log "카나리 헬스체크 실패 — 기존 버전을 유지한다(다운타임 없음)"
    sudo docker logs --tail 80 "${CANARY}" || true
    sudo docker rm -f "${CANARY}" || true
    exit 1
fi
log "카나리 헬스체크 통과"
sudo docker rm -f "${CANARY}" >/dev/null 2>&1 || true

# ── 3) 운영 컨테이너를 새 이미지로 교체(짧은 전환만 발생).
STEP=swap
log "운영 컨테이너 교체"
sudo docker stop "${APP}" >/dev/null 2>&1 || true
sudo docker rm   "${APP}" >/dev/null 2>&1 || true
sudo docker run -d --name "${APP}" --restart unless-stopped \
    -p "${BIND}:${PORT}:8000" "${APP}:${SHA}" \
    || fail_hard swap "앱 컨테이너 기동 실패"
log "앱 컨테이너 기동 완료"

ok=0
for _ in $(seq 1 15); do
    if curl -fsS "http://localhost:${PORT}/" >/dev/null 2>&1; then ok=1; break; fi
    sleep 2
done
[ "${ok}" = "1" ] || fail_hard swap "교체 후 앱이 ${PORT} 에서 응답하지 않는다"
log "앱 헬스체크 통과 (127.0.0.1:${PORT} — 외부 비공개)"

# ── 4) 리버스 프록시(80 → 8000). 공개 URL 에서 `:8000` 을 없애기 위한 것.
#      호스트 네트워크로 띄우고 127.0.0.1:${PORT} 로 넘긴다 — 앱 컨테이너가 교체돼도
#      호스트 포트는 그대로이므로 컨테이너 IP 를 추적할 필요가 없다.
STEP=proxy
PROXY_STATE="$(sudo docker inspect -f '{{.State.Running}}' "${PROXY}" 2>/dev/null || true)"
if [ "${PROXY_STATE}" = "true" ]; then
    log "프록시 실행 중 — 설정만 리로드(포트 80 다운타임 없음)"
    sudo docker exec "${PROXY}" nginx -t || fail_hard proxy "nginx 설정 검증 실패"
    sudo docker exec "${PROXY}" nginx -s reload || fail_hard proxy "nginx 리로드 실패"
else
    log "프록시 기동 (이전 상태=${PROXY_STATE:-없음})"
    sudo docker rm -f "${PROXY}" >/dev/null 2>&1 || true
    sudo docker run -d --name "${PROXY}" --restart unless-stopped \
        --network host \
        -v "${REPO_ROOT}/deploy/nginx.conf:/etc/nginx/conf.d/default.conf:ro" \
        nginx:1.27-alpine \
        || fail_hard proxy "프록시 기동 실패"
fi

STEP=verify
ok=0
for _ in $(seq 1 10); do
    if curl -fsS "http://localhost/" >/dev/null 2>&1; then ok=1; break; fi
    sleep 2
done
if [ "${ok}" != "1" ]; then
    log "프록시(포트 80) 헬스체크 실패 — 앱은 ${PORT} 에서 정상일 수 있다"
    sudo docker logs --tail 40 "${PROXY}" || true
    exit 1
fi
log "프록시 헬스체크 통과 (포트 80)"

# ── 5) 정리: dangling 이미지 + 최근 3개 SHA 이미지만 남긴다(이전 이미지는 롤백용으로 보존).
STEP=cleanup
sudo docker image prune -f >/dev/null 2>&1 || true
sudo docker images "${APP}" --format '{{.ID}} {{.Tag}}' \
    | grep -v ' latest$' \
    | awk 'NR>3 {print $1}' \
    | xargs -r sudo docker rmi >/dev/null 2>&1 || true
log "정리 완료"

STEP=done
