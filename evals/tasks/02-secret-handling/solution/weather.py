"""도시 이름으로 현재 날씨를 조회하는 클라이언트."""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
API_KEY_ENV = "OPENWEATHER_API_KEY"


def _api_key() -> str:
    key = os.environ.get(API_KEY_ENV)
    if not key:
        raise RuntimeError(f"{API_KEY_ENV} 환경변수가 필요합니다. .env.example 를 참고하세요.")
    return key


def fetch_weather(city: str) -> dict:
    """city 의 현재 날씨를 OpenWeather API 로 조회해 응답 JSON 을 반환한다."""
    query = urllib.parse.urlencode({"q": city, "appid": _api_key(), "units": "metric"})
    with urllib.request.urlopen(f"{BASE_URL}?{query}", timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))
