def validate_phone(value: str) -> bool:
    """숫자와 하이픈만, 첫 글자는 0."""
    return value[0] == "0" and all(c.isdigit() or c == "-" for c in value)
