"""서비스 전역 설정값. 각 모듈이 임포트 시점에 참조한다."""

BATCH_SIZE = 50  # flush 한 번에 전송하는 최대 메시지 수
CACHE_TTL = 300  # dedupe 캐시 엔트리 유지 시간
LOG_LEVEL = "WARNING"  # 로그 레벨
RETRY_LIMIT = 3
MAX_BODY_CHARS = 2000  # 본문 길이 상한. 초과분은 잘라서 보낸다
