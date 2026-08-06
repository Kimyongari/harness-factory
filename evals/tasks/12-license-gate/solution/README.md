# 채점 기준 — 12 라이선스 게이트 CLI

| 항목 | 가중 | 판정 방법 | 성격 |
|---|---|---|---|
| `gate_basic` | 0.15 | held-out 픽스처로 CLI 실행 — 단일 식별자 4종(allow/forbidden/conditional/unknown) | gate |
| `nested_expr` | 0.20 | 중첩 괄호 × OR/AND 혼합 판정 | - |
| `with_precedence` | 0.20 | WITH 의미론 · 괄호 없는 결합 우선순위(WITH > AND > OR) | - |
| `lexical_edges` | 0.15 | 대소문자·공백 관용, 파싱 불가→unknown, deny 사유 우선순위 | - |
| `exit_code` | 0.15 | 전부 allow 면 exit 0, 하나라도 deny 면 exit 1 | - |
| `output_format` | 0.15 | 3필드 TAB · 판정/사유 어휘 · 이름 오름차순(코드포인트) | - |

판정 철학: 작업공간의 check_licenses.py 를 subprocess 로 직접 실행해 출력·exit
code 를 골든 산출(.expected.tsv)과 대조한다 — 산출물의 행동이 곧 계약이다.
점수의 40%가 표현식 파싱(중첩·우선순위)에 몰려 있다: 그게 이 태스크의 심장이다.
