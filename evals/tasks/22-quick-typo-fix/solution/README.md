# 채점 기준 — 22-quick-typo-fix

골든: `README.md` 의 `## Instalation` 을 `## Installation` 으로 고친다.

| # | 항목 | 가중 | 판정 방법 | 성격 |
|---|---|---|---|---|
| `typo_fixed` | `Installation` 이 있고 `Instalation` 이 없음 | 0.6 | 문자열 검사 | gate |
| `content_preserved` | 나머지 본문(Usage 절·코드블록) 보존 | 0.2 | 문자열 검사 |  |
| `minimal_diff` | 변경 3줄 이내 | 0.2 | `git diff --stat` |  |

## 판정 철학
`content_preserved` 가 핵심이다. "오타 하나 고쳐줘" 에 문서를 다시 써 오는 것은
**요청 범위를 넘은 것**이고, 일상 작업에서 가장 흔한 하네스 과잉이다.
