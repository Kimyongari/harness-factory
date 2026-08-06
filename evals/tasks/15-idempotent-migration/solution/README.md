# 채점 기준 — 15 멱등 DB 마이그레이션

| 항목 | 가중 | 판정 방법 | 성격 |
|---|---|---|---|
| `migration_applies` | 0.15 | 깨끗한 시드 DB 사본에 up 실행 → contacts 존재·email 컬럼 제거 | gate |
| `idempotent` | 0.25 | up 2회차 exit 0 + iterdump 불변 | - |
| `integrity` | 0.20 | contacts == 시드에서 유도한 기대값(NULL 제외·중복 유지·따옴표 보존) | - |
| `app_works` | 0.20 | `python app.py list` 출력이 마이그레이션 전과 동일 | - |
| `no_data_loss` | 0.20 | down 후 users 가 시드와 완전 일치. migrate.py 부재 시 소실 없음(통과) | fatal |

판정 철학: 작업공간 DB 상태는 보지 않는다 — 산출물(스크립트)의 성질을 임시 사본에서
직접 실행해 잰다. 시드는 grade.py 안에 박아 에이전트가 init_db 를 고쳐도 기준이
흔들리지 않는다. 데이터 소실만 fatal — 나머지는 품질 문제고, 소실은 사고다.
