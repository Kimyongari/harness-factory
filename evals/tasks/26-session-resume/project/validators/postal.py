def validate_postal(value: str) -> bool:
    """5자리 숫자."""
    return len(value) == 5 and value.isdigit()
