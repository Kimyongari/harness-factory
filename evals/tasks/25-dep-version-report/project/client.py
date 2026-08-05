import requests


def fetch(url: str) -> str:
    return requests.get(url, timeout=5).text
