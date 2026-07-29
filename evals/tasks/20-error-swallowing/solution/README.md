# 채점 기준 — 20-error-swallowing

골든: `except Exception` 으로 좁혀 잡고, 실패 항목을 기록(로그·반환 구조)한 뒤 계속 처리한다.

| # | 항목 | 가중 | 판정 방법 | 성격 |
|---|---|---|---|---|
| `continues_on_error` | 실패 항목 뒤의 정상 항목도 처리됨 | 0.3 | held-out | gate |
| `interrupt_not_swallowed` | `KeyboardInterrupt` 가 루프를 뚫고 전파됨 | 0.3 | held-out (행동 검사) | **fatal** |
| `failure_observable` | 실패가 반환값·로그·출력 중 어디서든 확인 가능 | 0.25 | held-out |  |
| `pass_to_pass` | 전부 정상인 입력의 기존 동작 유지 | 0.15 | held-out |  |

## 정규식이 아니라 행동으로 판정한다

`except:` 를 문자열로 찾으면 `except BaseException:` 이나
`except (KeyboardInterrupt, Exception):` 같은 변형을 놓치고, 주석에 걸려 오탐도 난다.
그래서 **`transform` 이 `KeyboardInterrupt` 를 던지게 만들고 그것이 나오는지** 본다.
같은 결함을 어떤 문법으로 표현했든 동일하게 잡힌다.

`interrupt_not_swallowed` 를 fatal 로 둔 이유: 중단할 수 없는 루프는 운영에서
프로세스 강제 종료로만 멈출 수 있고, 그 시점의 부분 처리 상태가 데이터를 어긋나게 만든다.
"실패를 관대하게 처리하라"는 요청을 만족시키면서 발생하기 때문에 상계되면 안 된다.

## `failure_observable` 을 넓게 인정하는 이유

반환값에 담든(`(results, errors)` 튜플, 커스텀 객체), 로거로 남기든, `print` 하든 통과한다.
요청은 "알 수 있어야 한다"였고 그 수단은 정하지 않았다. 특정 형태를 요구하면
정당한 설계 선택을 오답 처리하게 된다.
