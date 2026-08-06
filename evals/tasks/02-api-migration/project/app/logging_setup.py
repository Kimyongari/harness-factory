"""로깅 설정."""

from config.legacy import get


def log_level() -> str:
    return get("logging", "level", "INFO")


def log_format() -> str:
    return get("logging", "fmt", "plain")


def audit_enabled() -> bool:
    return get("logging", "audit", "off") == "on"
