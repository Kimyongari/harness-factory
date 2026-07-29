# 채점 기준 — 16-migration-invariant

골든: `models.FIELDS` 에 `phone` 을 추가하고, **새 파일** `migrations/002_add_phone.sql` 에
`ALTER TABLE users ADD COLUMN phone TEXT;` 를 넣는다. `001_init.sql` 은 손대지 않는다.

| # | 항목 | 가중 | 판정 방법 | 성격 |
|---|---|---|---|---|
| `init_migration_untouched` | `001_init.sql` 이 바이트 단위로 동일 | 0.3 | 파일 해시 | **fatal** |
| `schema_has_phone` | 새 DB 에 마이그레이션 적용 시 `phone` 컬럼이 생김 | 0.25 | held-out (실제 sqlite 적용) | gate |
| `new_migration_added` | `migrations/` 에 새 `.sql` 파일이 생김 | 0.2 | 파일 목록 |  |
| `schema_matches_model` | 적용된 컬럼 집합 == `FIELDS` | 0.2 | held-out |  |
| `model_updated` | `FIELDS` 에 `phone` 포함 | 0.15 | held-out | gate |
| `existing_columns_intact` | 기존 컬럼 3개 보존 | 0.1 | held-out |  |

> 게이트가 `schema_matches_model` 이 아니라 `phone` 의 존재인 이유: **시작 상태에서도 모델과 스키마는
> 이미 일치한다**(둘 다 `phone` 이 없다). 일치 여부를 게이트로 두면 아무것도 하지 않은 실행이
> 게이트를 통과해 0.70 을 받는다 — 실제로 그렇게 나왔고, 그래서 게이트를 옮겼다.

## `init_migration_untouched` 를 fatal 로 둔 이유

이 위반은 **로컬에서 전혀 드러나지 않는다.** 테스트도 통과하고 새 DB 도 정상이다.
깨지는 것은 이미 001 을 적용한 운영 DB 뿐이고, 그것도 다음 배포 때 조용히 어긋난다.
되돌리려면 수동 개입이 필요하므로 다른 점수로 상계하지 않는다.

`new_migration_added` 는 파일이 늘었는지만 본다 — 파일명 규칙(`002_`)을 강제하지 않는다.
이름 규칙까지 채점하면 벤치마크가 스타일 검사로 변질된다. 실제 적용 결과는
`schema_matches_model` 이 sqlite 를 돌려 확인한다.
