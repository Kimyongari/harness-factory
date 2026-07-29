# 채점 기준 — 01-fix-failing-test

골든: `add` 가 `a + b` 를 반환한다. 그 외 변경 없음.

| # | 항목 | 가중 | 판정 방법 |
|---|---|---|---|
| `fail_to_pass` | `add` 가 5개 케이스 전부에서 합을 반환 | 0.6 | held-out pytest |
| `pass_to_pass` | `multiply` 회귀 없음 | 0.3 | held-out pytest |
| `scope` | 변경이 `add` 한 줄 범위 (diff ≤ 12줄) | 0.1 | `git diff` 라인 수 |

`scope` 는 감점용 소가중치다 — 정답은 맞았지만 불필요하게 넓게 고친 경우를 잡는다.
