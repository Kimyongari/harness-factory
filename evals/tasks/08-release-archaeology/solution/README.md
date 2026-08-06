# 채점 기준 — 08 릴리스 고고학

| 항목 | 가중 | 판정 방법 | 성격 |
|---|---|---|---|
| `answers_schema` | 0.05 | answers.json 존재 + q1~q4 answer/evidence 구조 | gate |
| `format` | 0.10 | 버전 표기 v0.X · q4 오름차순·타입 · evidence 대응 길이 | - |
| `q1_answer` | 0.15 | check 반환 타입이 바뀐 첫 버전 = v0.5 | - |
| `q2_introduced` / `q2_fixed` | 각 0.075 | 음수 remaining 버그 도입 v0.3 / 수정 v0.8 | - |
| `q3_answer` | 0.15 | CHANGES.md 와 코드가 모순되는 버전 = v0.6 | - |
| `q4_answer` | 0.15 | WINDOW_SECONDS 이력 (v0.1,60)→(v0.4,30)→(v0.7,45) 완전 일치 | - |
| `ev_q1`~`ev_q4` (5개) | 각 0.05 (합 0.25) | 인용 file:line 을 pristine project/ 에서 열어 허용 정규식(±1줄)과 대조 | - |

판정 철학: 조사는 읽기 작업이므로 증거는 pristine 사본에서 검증해 소스 조작을
무력화한다. 답 정확도(60%)가 몸통이고 증거(25%)는 답이 맞을 때만 인정한다.
지어낸 근거가 하나라도 있으면 evidence 전 항목 0.
