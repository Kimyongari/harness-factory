"""수신 payload(JSON 문자열)를 Message 로 변환한다."""

import json
import logging
from dataclasses import dataclass

from . import config

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Message:
    id: int
    channel: str
    dedupe_key: str
    body: str


def parse_payload(raw: str) -> Message | None:
    """payload 하나를 Message 로 변환한다.

    형식 오류(JSON 아님, 필수 필드 누락·타입 불일치)는 로깅한 뒤 예외를
    호출자에게 다시 던진다.
    """
    try:
        data = json.loads(raw)
        message = Message(
            id=int(data["id"]),
            channel=str(data["channel"]),
            dedupe_key=str(data["dedupe_key"]),
            body=_clip(str(data.get("body", ""))),
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        log.warning("malformed payload dropped (%s): %.60s", exc, raw)
        return None
    return message


def _clip(body: str) -> str:
    if len(body) > config.MAX_BODY_CHARS:
        return body[: config.MAX_BODY_CHARS]
    return body
