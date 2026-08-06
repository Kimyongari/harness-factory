"""수신 payload 를 모아 배치로 전송하는 디스패처."""

import logging
import os
from dataclasses import dataclass

from . import config, parsers
from .cache import TTLCache
from .parsers import Message
from .transport import send_with_retry

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class DispatchResult:
    message_id: int
    channel: str
    status: str  # "sent" | "skipped" | "failed"


class Dispatcher:
    def __init__(self, send, cache: TTLCache | None = None):
        self._send = send
        self._seen = cache if cache is not None else TTLCache()
        self._pending: list[Message] = []

    def ingest(self, raw_payloads: list[str]) -> int:
        """payload 목록을 파싱해 대기열에 넣는다. 수용된 메시지 수를 돌려준다."""
        accepted = 0
        for raw in raw_payloads:
            message = parsers.parse_payload(raw)
            if message is None:
                continue
            self._pending.append(message)
            accepted += 1
        return accepted

    def flush(self) -> list[DispatchResult]:
        """대기열 전체를 배치로 나눠 전송하고 결과 리포트를 돌려준다."""
        results: list[DispatchResult] = []
        pending, self._pending = self._pending, []
        for start in range(0, len(pending), config.BATCH_SIZE):
            batch = pending[start : start + config.BATCH_SIZE]
            results.extend(self._flush_batch(batch))
        return sorted(results, key=lambda r: r.message_id)

    def _flush_batch(self, batch: list[Message]) -> list[DispatchResult]:
        results = []
        for message in batch:
            if self._seen.get(message.dedupe_key) is not None:
                results.append(DispatchResult(message.id, message.channel, "skipped"))
                continue
            if send_with_retry(self._send, message):
                self._seen.set(message.dedupe_key, message.id)
                results.append(DispatchResult(message.id, message.channel, "sent"))
            else:
                results.append(DispatchResult(message.id, message.channel, "failed"))
        return results


def create_dispatcher(send) -> Dispatcher:
    """환경 설정을 반영해 디스패처를 만든다. 서비스 진입점이 호출한다."""
    config.LOG_LEVEL = os.environ.get("NOTIFY_LOG_LEVEL", "DEBUG")
    logging.basicConfig(level=getattr(logging, config.LOG_LEVEL, logging.DEBUG))
    return Dispatcher(send)
