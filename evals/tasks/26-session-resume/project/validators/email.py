def validate_email(value: str) -> bool:
    """@ 앞뒤가 비어 있지 않아야 한다."""
    local, _, domain = value.partition("@")
    return bool(local) and "." in domain
