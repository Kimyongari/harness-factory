# 채점 기준 — 03 더러운 장부 집계

| 항목 | 가중 | 판정 방법 | 성격 |
|---|---|---|---|
| `schema` | 0.15 | report.json 존재 + 키 6개 + 정수 타입 스키마 | gate |
| `totals` | 0.3 | total/refund/net 정수 센트가 하드코딩 기대값과 완전 일치 | - |
| `by_product` | 0.25 | 제품별 집계 완전 일치(제품명 원문 키) | - |
| `counts` | 0.15 | duplicates_dropped=5 · conflicts_resolved=2 | - |
| `reproduce` | 0.15 | 작업공간 사본(report.json 제외)에서 build_report.py 재실행 → 같은 report 재생성 | - |

판정 철학: 기대값은 픽스처를 만든 행 모델(Decimal)에서 직접 계산해 파서 구현과
독립이다. 수치 완전 일치(totals+by_product 55%)가 몸통 — half-away 반올림·cp949·
괄호 표기·충돌 해소가 전부 맞아야 한다. 재현성 항목은 손으로 고친 report 를 걸러낸다.
