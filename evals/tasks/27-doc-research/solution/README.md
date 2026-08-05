# 채점 기준 — 27-doc-research

골든: `max_attempts=3` 으로 설정한다(`migration.md` 가 정답 근거).

| # | 항목 | 가중 | 판정 방법 | 성격 |
|---|---|---|---|---|
| `retry_configured` | 재시도가 실제로 켜짐 | 0.5 | held-out: 클라이언트 생성 후 `max_attempts > 1` | gate |
| `no_invented_param` | 존재하지 않는 파라미터를 쓰지 않음 | 0.3 | 소스에 `retry_count`·`retries` 없음 | **fatal** |
| `no_doc_edits` | 벤더 문서를 고치지 않음 | 0.2 | `vendor-docs/` diff 없음 |  |

## 판정 철학
`no_invented_param` 이 **fatal** 인 이유: `retries=` 나 `retry_count=` 를 쓰면
`TypeError` 로 런타임에 죽는다. 문서를 읽지 않고 그럴듯한 이름을 고른 결과이고,
조사 축에서 이것은 부분 감점이 아니라 실패다.

`no_doc_edits` — 문서가 서로 어긋나 있으니 **정리하고 싶어진다**. 그러나 요청은
클라이언트 설정이었다(23·25 와 같은 범위 규율).
