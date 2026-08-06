"""전송 계층. 실제 네트워크 대신 주입된 send 콜러블을 사용한다."""

import logging
import time

from . import config
from .parsers import Message

log = logging.getLogger(__name__)


class TransportError(Exception):
    """일시적 전송 실패. 재시도 대상이다."""


def send_with_retry(send, message: Message, sleep=time.sleep) -> bool:
    """message 를 전송한다. TransportError 는 최대 5회까지 재시도한다.

    재시도 사이의 대기는 지수 백오프를 따른다. 모든 시도가 실패하면 False 를
    돌려준다. TransportError 이외의 예외는 그대로 전파된다.
    """
    for attempt in range(config.RETRY_LIMIT):
        try:
            send(message)
            return True
        except TransportError as exc:
            log.warning("send failed (attempt %d): %s", attempt + 1, exc)
            if attempt < config.RETRY_LIMIT - 1:
                sleep(2**attempt)
    return False
