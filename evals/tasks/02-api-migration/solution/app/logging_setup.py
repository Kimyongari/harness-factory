"""로깅 설정."""

from config.store import lookup


def log_level() -> str:
    return lookup("logging.level", default="INFO")


def log_format() -> str:
    return lookup("logging.fmt", default="plain")


def audit_enabled() -> bool:
    return lookup("logging.audit", default="off") == "on"
