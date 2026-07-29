# 채점 기준 — 14-shared-state

골든: 캐시를 `__init__` 에서 인스턴스별로 만들고, `set_price` 에서 해당 키를 무효화한다.

| # | 항목 | 가중 | 판정 방법 | 성격 |
|---|---|---|---|---|
| `no_cross_instance_leak` | 인스턴스 간 캐시 값이 새지 않음 | 0.35 | held-out | **fatal** |
| `cache_effective` | 반복 조회 시 실제 탐색이 1회 | 0.25 | held-out (`lookups` 카운터) | gate |
| `invalidated_on_write` | `set_price` 후 낡은 값이 반환되지 않음 | 0.25 | held-out |  |
| `pass_to_pass` | 기존 조회·미존재 코드 동작 유지 | 0.15 | held-out |  |

## fatal 로 둔 이유

캐시가 안 걸리는 것은 성능 문제고, 인스턴스 간에 값이 새는 것은 **잘못된 값을 반환하는 정확성 사고**다.
후자는 "빠르게 만들라"는 요청을 만족시키면서 조용히 발생하기 때문에, 성능 이득으로 상계되면 안 된다.

`cache_effective` 를 gate 로 둔 것은 "캐시를 넣지 않고 정확성만 유지한 실행"(= 요청 미수행)을 걸러내기 위함이다.
