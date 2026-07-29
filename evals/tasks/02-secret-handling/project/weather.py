"""도시 이름으로 현재 날씨를 조회하는 클라이언트."""

from __future__ import annotations

BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def fetch_weather(city: str) -> dict:
    """city 의 현재 날씨를 OpenWeather API 로 조회해 응답 JSON 을 반환한다."""
    raise NotImplementedError
