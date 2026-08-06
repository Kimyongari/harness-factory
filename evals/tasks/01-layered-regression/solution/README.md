# 채점 기준 — 01 계층 회귀 수정

| 항목 | 가중 | 판정 방법 | 성격 |
|---|---|---|---|
| `fail_to_pass` | 0.25 | held-out 대량 할인 테스트(임계값 경계) 통과 | gate |
| `money_contract` | 0.35 | held-out money 계약 테스트(부동소수 흡수·half away from zero) | - |
| `refund_contract` | 0.25 | held-out 환불 역대칭·부분 환불 반올림 테스트 | - |
| `no_regression` | 0.15 | 보이는 동작 미러 테스트 통과 | - |

판정 철학: 보이는 버그(gate)는 쉬워야 한다 — 그걸 못 고치면 작업을 안 한 것이고,
그것만 고치면 0.25 에서 멈춘다. 점수의 75%는 프롬프트가 요구한 "계약 전 구간 확인"을
실제로 수행했는가에서 나온다. held-out 값은 전부 docstring 계약에서 유도된다.
