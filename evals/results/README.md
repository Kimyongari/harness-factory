# 실행 결과 보관소

해석부터 읽으려면 → **[`FINDINGS.md`](FINDINGS.md)**. 최신 숫자만 보려면 → **[`LATEST.md`](LATEST.md)**.

결과는 **타깃별 폴더**로 정리한다. 세 폴더의 README 는 같은 목차(개요 → 실행 설정 →
실행 이력 → 최신 결과 요약 → 알려진 주의사항 → 재현 방법)를 쓴다.

| 폴더 | 내용 |
|---|---|
| [`claude-code/`](claude-code/README.md) | Claude Code 실행 결과 (최신: 2026-07-30, opus-5 와 haiku-4-5 각각 effort high) |
| [`codex/`](codex/README.md) | Codex 실행 결과 (최신: 2026-07-29, gpt-5.6-sol · reasoning high) |
| [`cursor/`](cursor/README.md) | Cursor - 아직 실행 이력 없음 (CLI 미설치) |

## 폴더 규약

실행 하나가 디렉터리 하나다. 이름은 `<타깃>/<YYYYMMDD>-<모델>-<추론수준>-<범위>/`.
`python -m evals.abrun` 은 결과를 이 디렉터리 루트에 `<타임스탬프>-<모드>/` 로 만들므로,
실행이 끝나면 타깃 폴더로 옮기고 이름을 규약에 맞춘 뒤 그 폴더 README 의 실행 이력 표에 한 줄 적는다.

| 파일 | 내용 |
|---|---|
| `summary.json` | 전체 실행의 원시 데이터 - 태스크·조건·점수·항목별 판정·토큰·시간·비용 |
| `scorecard.md` | 사람이 읽는 요약 (`python -m evals.scorecard` 이 생성) |
| `LATEST.md` | 가장 최근 agent 실행의 스코어카드 사본 (이 디렉터리 루트) |
| `FINDINGS.md` | **결과 해석** - 숫자를 어떻게 읽어야 하는가, 발견한 채점기 버그, 실행 이력 (사람이 작성) |

## 모드별로 무엇을 확인하나

| 모드 | 기대 결과 | 용도 |
|---|---|---|
| `golden` | 전부 1.00 | 채점기가 정답을 인정하는가 (false negative 검사) |
| `baseline` | 전부 ≤ 0.15 | 채점기가 미수행을 걸러내는가 (false positive 검사) |
| `agent` | 측정값 | 실제 A/B 결과 |

`golden` · `baseline` 이 기대를 벗어난 상태의 `agent` 결과는 읽지 않는다.
두 모드는 LLM 을 호출하지 않으므로 CI(`python -m evals.run`)에서 항상 돈다.

## 타깃 간 비교 시 주의

- 채점기 버전이 실행마다 다를 수 있다 - 각 타깃 README 의 "채점기 버전" 행을 먼저 확인한다.
  특히 PR [#24](https://github.com/Kimyongari/harness-factory/pull/24) 이전 실행은 커밋 게이트
  편향의 영향을 받을 수 있다([`codex/README.md`](codex/README.md) 5절의 파생 보정 참고).
- 비용 지표는 도구마다 노출 범위가 다르다(Codex 는 `cost_usd`·턴 수 없음).

## 트랜스크립트는 어디에

작업공간과 실행 트랜스크립트(`transcript.jsonl`, `final_message.txt`)는 레포 밖
`EVAL_WORKROOT`(기본 `$TMPDIR/harness-eval`)에 남는다. 커밋하지 않는다 - 용량이 크고,
태스크 픽스처의 가짜 크레덴셜이 그대로 들어 있다. 각 실행의 `summary.json` 에 경로가 적혀 있다.
