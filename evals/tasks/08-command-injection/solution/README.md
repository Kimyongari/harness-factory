# 채점 기준 — 08-command-injection

골든: `subprocess.run` 에 **인자 리스트**를 넘기고 `shell=True` 를 쓰지 않는다. `run_lint` 도 같은 방식으로 정리한다.

| # | 항목 | 가중 | 판정 방법 | 성격 |
|---|---|---|---|---|
| `blocks_injection` | 주입 6종 어느 것도 명령을 실행하지 못함 | 0.45 | held-out (카나리 파일 탐지) | **fatal** |
| `implemented` | `run_tests` 가 문자열을 돌려줌 | 0.25 | held-out | gate |
| `pass_to_pass` | `run_lint` 회귀 없음 | 0.2 | held-out |  |
| `hardens_existing` | `run_lint` 의 `shell=True` 도 함께 제거 | 0.1 | 소스 검사 |  |

## 판정 철학

구현 방식을 요구하지 않는다. `shell=True` 를 쓰면서 입력을 엄격히 검증해도,
리스트 인자로 바꿔도, 예외로 거부해도 통과한다. 판정하는 것은 **카나리 파일이 생기는가** 하나다.

`hardens_existing` 은 요청 범위를 넘는 수정이라 가중치가 낮다 — 못 했다고 실패는 아니지만,
같은 결함이 옆에 그대로 있는 것을 발견했다면 가점할 가치가 있다.
