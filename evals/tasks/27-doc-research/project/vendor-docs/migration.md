# v1 → v2 마이그레이션

## 변경된 파라미터

| v1 | v2 | 비고 |
|---|---|---|
| `retries` | `max_attempts` | 의미도 바뀜: **총 시도 횟수**(재시도 횟수가 아님) |
| `timeout_ms` | `timeout` | 초 단위 float |

v2 에서 3회까지 시도하려면:

```python
PaymentsClient(api_key, max_attempts=3)
```
