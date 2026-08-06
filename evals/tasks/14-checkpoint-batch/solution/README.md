# 채점 기준 — 14 체크포인트 배치 재개

| 항목 id | 가중 | 판정 방법 | 성격 |
|---|---|---|---|
| `journal_exists` | 0.15 | output/journal.tsv 존재 + 재계산 체크섬과 일치하는 유효 항목 ≥ 1 | gate |
| `exactly_once` | 0.35 | 유효 288건이 journal 에 각각 정확히 한 번(중복·누락·잉여 없음) | - |
| `checksums` | 0.20 | journal 전행의 체크섬이 spec 정규화 규칙 재계산과 일치 | - |
| `errors_exact` | 0.15 | errors.tsv 가 포이즌 12건과 정확히 일치(각 1회·사유 비어 있지 않음) | - |
| `idempotent` | 0.15 | 채점기가 process.py 를 한 번 더 실행 → journal/errors 바이트 불변 | - |
| `inbox_preserved` | 0.0 | inbox 300건이 held-out 생성 원문과 바이트 동일(읽기 전용 계약) | fatal |

판정 철학: 기대값은 작업공간을 신뢰하지 않고 held-out 사본 생성기에서 독립
재계산하며, 점수의 절반은 "처리했는가"가 아니라 "중단·재개·재실행 어디서도 정확히
한 번인가"(exactly_once + idempotent)라는 연속성 계약에서 나온다.
