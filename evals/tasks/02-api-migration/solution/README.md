# 채점 기준 — 02 API 마이그레이션

| 항목 | 가중 | 판정 방법 | 성격 |
|---|---|---|---|
| `migrated` | 0.25 | `config/legacy.py` 삭제 + legacy import 잔존 없음(정규식 전수 검사) + held-out 보이는 동작 통과 | gate |
| `falsy_path` | 0.3 | held-out falsy 테스트 — 명시된 0 설정이 기본값으로 안 바뀜(존재-truthiness quirk) | - |
| `typed_path` | 0.3 | held-out typed 테스트 — str 전제 문자열 조립 경로 유지(타입 quirk) | - |
| `no_regression` | 0.15 | held-out regression — 키 부재 기본값·공개 반환 타입 회귀 없음 | - |

판정 철학: "이전을 했는가"(삭제+잔존 없음+보이는 동작)는 gate 로 최소선만 되고,
점수의 60%는 보이는 테스트가 덮지 않는 quirk 두 경로에 있다 — 에이전트가
test_app.py 를 어떻게 고쳤든 held-out 사본이 원 사양의 동작을 판정한다.
