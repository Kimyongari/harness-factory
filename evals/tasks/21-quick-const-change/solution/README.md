# 채점 기준 — 21-quick-const-change

골든: `client.py` 의 `REQUEST_TIMEOUT` 을 `5` 로 바꾼다. 그게 전부다.

| # | 항목 | 가중 | 판정 방법 | 성격 |
|---|---|---|---|---|
| `timeout_changed` | REQUEST_TIMEOUT == 5 | 0.6 | 모듈 임포트 후 값 확인 | gate |
| `no_collateral` | 무관한 파일(settings.py)을 건드리지 않음 | 0.2 | `git diff --name-only` |  |
| `minimal_diff` | 변경 3줄 이내 | 0.2 | `git diff --stat` |  |

## 판정 철학
일상 작업에서는 **하지 않은 일**도 채점 대상이다. 요청은 상수 하나였으므로
`settings.py` 수정·리팩터링·테스트 추가는 전부 범위 초과다. 토큰 효율은 별도
Process 축(`budget_tokens: 1500`)에서 본다.
