def validate_url(value: str) -> bool:
    """http/https 로 시작해야 한다."""
    if not value:
        return False
    scheme = value.split("://")[0]
    return scheme in ("http", "https")
