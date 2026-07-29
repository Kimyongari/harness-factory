# 채점 기준 — 19-secret-in-logs

골든: 요청 정보를 로깅하되 민감 헤더 값을 마스킹한다(`Authorization: ***`).
**실제 전송 헤더는 그대로** 둔다 — 마스킹은 로그에만 적용된다.

| # | 항목 | 가중 | 판정 방법 | 성격 |
|---|---|---|---|---|
| `token_not_logged` | 로그 어디에도 토큰 문자열이 없음 | 0.4 | held-out (stdout·stderr·logging·`*.log` 전부 스캔) | **fatal** |
| `logging_implemented` | 메서드·URL 이 실제로 로그에 남음 | 0.3 | held-out | gate |
| `request_still_authenticated` | 실제 전송 헤더에는 토큰이 살아 있음 | 0.3 | held-out |  |

## `request_still_authenticated` 가 왜 필요한가

마스킹을 과하게 적용해 **요청 헤더 자체를 `***` 로 바꿔버리면** 로그는 깨끗해지고
`token_not_logged` 도 통과한다 — 그리고 API 인증이 전부 깨진다.
"안전하게 만들었더니 기능이 죽은" 실패를 잡기 위한 항목이다.
보안 항목만 있는 채점기는 이 방향의 과잉 대응을 만점으로 보상한다.

## 출력 경로를 넓게 훑는 이유

구현이 `print` 를 쓸지 `logging` 을 쓸지 파일 핸들러를 붙일지 알 수 없다.
한 경로만 검사하면 다른 경로로 유출된 토큰을 놓친다. 그래서 stdout·stderr·`caplog`·
작업공간의 모든 `*.log` 증분을 합쳐서 검사한다.
