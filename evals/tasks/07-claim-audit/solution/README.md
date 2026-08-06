# 채점 기준 — 07 주장 감사

| 항목 | 가중 | 판정 방법 | 성격 |
|---|---|---|---|
| `audit_schema` | 0.05 | audit.json 존재 + 스키마(배열 10원소·claim 1..10·verdict·evidence.file/line) | gate |
| `format` | 0.10 | claim 오름차순 정렬 + 엄격 타입(verdict bool·line 양의 int) | - |
| `verdict_1`~`verdict_10` | 각 0.05 (합 0.5) | 주장별 판정을 정답표와 비교 | - |
| `evidence_1`~`evidence_10` | 각 0.035 (합 0.35) | 인용 file:line 을 pristine project/ 에서 열어 허용 정규식(±1줄)과 대조 | - |

판정 철학: 감사는 읽기 작업이므로 증거는 에이전트 작업공간이 아니라 pristine
사본에서 검증한다 — 소스를 고쳐 증거를 "만드는" 조작이 무력화된다. 지어낸
근거(실재하지 않는 파일·줄)가 하나라도 있으면 evidence 전 항목 0. 판정이 틀린
주장의 증거도 불인정 — 증거는 맞는 판정에 대한 근거일 때만 점수다.
