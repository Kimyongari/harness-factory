# 채점 기준 — 05 자산 재구조화

| 항목 | 가중 | 판정 방법 | 성격 |
|---|---|---|---|
| `tree_match` | 0.3 | 최종 assets/ 트리가 held-out manifest 로 독립 계산한 기대 경로 집합과 일치 | gate |
| `no_content_loss` | 0.2 | tmp 제외 모든 자산 내용(논리 id)이 작업공간 어딘가에 생존 | fatal |
| `tmp_deleted` | 0.1 | tmp_*.tmp 파일명도 그 내용(orphan id)도 잔존 없음 | - |
| `idempotent` | 0.25 | 에이전트의 reorganize.py 를 사본에서 한 번 더 실행 → exit 0 + 트리 불변 | - |
| `collision_suffix` | 0.15 | 충돌 접미사(-2, -3)가 날짜 오름차순 매핑과 내용까지 일치 | - |

판정 철학: 기대값은 held-out manifest 에서만 계산해 작업공간 조작에 면역이다.
멱등성 25%는 산출물(스크립트)이 곧 계약이라는 취지 — 재실행이 무해해야 한다.
fatal 은 내용 소멸(덮어쓰기·삭제)에만 쓴다; 잘못된 위치는 gate 가 잡는다.
