"""아주 작은 CSV 파서."""


def parse(text: str) -> list[list[str]]:
    return [line.split(",") for line in text.strip().splitlines()]
