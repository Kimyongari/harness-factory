"""채점 전용 기준 데이터 — project/incident/metrics.csv 와 같은 값의 단일 원본.

grade.py 는 작업공간의 CSV(에이전트가 수정할 수 있다)가 아니라 이 모듈에서
기대값을 독립 계산한다. project 쪽 CSV 는 이 모듈의 rows() 를 그대로 덤프해 만들었다.
"""

from datetime import datetime, timedelta

BASE = datetime(2026, 7, 22, 13, 0)  # UTC
MINUTES = 180
THRESHOLD = 50  # 장애 정의: error_count >= 50 이 5분 이상 연속
MIN_RUN = 5

# 레드 헤링: 13:21~13:25 상승 — 연속 >=50 은 4분(13:22~13:25)뿐이라 장애 정의 미달.
_RED_HERRING = {21: 42, 22: 55, 23: 65, 24: 58, 25: 51}
# 실제 장애: 14:07~14:38, 32분 연속 >=50.
_INCIDENT_START = 67
_INCIDENT_ERRORS = [
    58, 84, 121, 160, 203, 259, 301, 344, 380, 402, 396, 371,
    355, 340, 322, 305, 298, 310, 287, 265, 240, 212, 188, 161,
    142, 118, 95, 82, 74, 66, 57, 52,
]  # fmt: skip
# 장애 전후 완만한 램프(임계 미만).
_RAMP = {65: 6, 66: 23, 99: 12}


def _error_at(i: int) -> int:
    if i in _RED_HERRING:
        return _RED_HERRING[i]
    if i in _RAMP:
        return _RAMP[i]
    if _INCIDENT_START <= i < _INCIDENT_START + len(_INCIDENT_ERRORS):
        return _INCIDENT_ERRORS[i - _INCIDENT_START]
    return (i * 7) % 4  # 평시 노이즈 0~3


def rows() -> list[tuple[str, int, int]]:
    """(UTC ISO 타임스탬프, error_count, request_count) 180행."""
    out = []
    for i in range(MINUTES):
        ts = (BASE + timedelta(minutes=i)).strftime("%Y-%m-%dT%H:%M:%SZ")
        out.append((ts, _error_at(i), 1900 + (i * 37) % 180))
    return out


def incident_window() -> dict:
    """장애 정의를 적용해 기대값을 계산한다 — 채점기의 독립 산정."""
    data = rows()
    runs: list[list[int]] = []
    cur: list[int] = []
    for i, (_, err, _) in enumerate(data):
        if err >= THRESHOLD:
            cur.append(i)
        else:
            if len(cur) >= MIN_RUN:
                runs.append(cur)
            cur = []
    if len(cur) >= MIN_RUN:
        runs.append(cur)
    assert len(runs) == 1, f"장애 정의를 만족하는 구간이 1개여야 한다: {len(runs)}"
    win = runs[0]
    errors = [data[i][1] for i in win]
    return {
        "start": data[win[0]][0],
        "end": data[win[-1]][0],
        "duration_min": len(win),
        "failed_requests": sum(errors),
        "peak_errors": max(errors),
    }


CAUSE_DEPLOY = "deploy-2093"  # 23:03:12 KST = 14:03:12 UTC, 장애 시작 4분 전
ALL_DEPLOYS = ["deploy-2081", "deploy-2087", "deploy-2093", "deploy-2094", "deploy-2095"]
