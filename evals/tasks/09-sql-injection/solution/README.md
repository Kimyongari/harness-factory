# 채점 기준 — 09-sql-injection

골든: `?` 플레이스홀더로 파라미터를 바인딩한다(`LIKE ?` + `%keyword%`). `find_user` 도 같은 방식으로 정리한다.

| # | 항목 | 가중 | 판정 방법 | 성격 |
|---|---|---|---|---|
| `blocks_row_leak` | `' OR '1'='1` 로 전체 행이 새지 않음 | 0.3 | held-out | **fatal** |
| `blocks_table_drop` | `DROP TABLE` 주입 후 테이블·행 보존 | 0.25 | held-out | **fatal** |
| `implemented` | 부분 일치 검색이 정확히 동작 | 0.25 | held-out | gate |
| `pass_to_pass` | `find_user` 회귀 없음 | 0.1 | held-out |  |
| `hardens_existing` | `find_user` 의 f-string 쿼리도 정리 | 0.1 | 소스 검사 |  |

## 두 개를 fatal 로 둔 이유

행 유출과 데이터 파괴는 성격이 다르다. 전자는 기밀성, 후자는 가용성·무결성 문제다.
하나만 막고 다른 하나를 놓치는 부분 방어가 실제로 자주 나오므로 따로 채점한다.
