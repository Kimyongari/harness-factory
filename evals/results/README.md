# 실행 결과 보관소

실행 하나가 디렉터리 하나다: `<타임스탬프>-<모드>/`

| 파일 | 내용 |
|---|---|
| `summary.json` | 전체 실행의 원시 데이터 — 태스크·조건·점수·항목별 판정·토큰·시간·비용 |
| `scorecard.md` | 사람이 읽는 요약 (`python -m evals.scorecard` 이 생성) |
| `LATEST.md` | 가장 최근 agent 실행의 스코어카드 사본 (이 디렉터리 루트) |

## 모드별로 무엇을 확인하나

| 모드 | 기대 결과 | 용도 |
|---|---|---|
| `golden` | 전부 1.00 | 채점기가 정답을 인정하는가 (false negative 검사) |
| `baseline` | 전부 ≤ 0.15 | 채점기가 미수행을 걸러내는가 (false positive 검사) |
| `agent` | 측정값 | 실제 A/B 결과 |

`golden` · `baseline` 이 기대를 벗어난 상태의 `agent` 결과는 읽지 않는다.
두 모드는 LLM 을 호출하지 않으므로 CI(`python -m evals.run`)에서 항상 돈다.

## 트랜스크립트는 어디에

작업공간과 실행 트랜스크립트(`transcript.jsonl`, `final_message.txt`)는 레포 밖
`EVAL_WORKROOT`(기본 `$TMPDIR/harness-eval`)에 남는다. 커밋하지 않는다 — 용량이 크고,
태스크 픽스처의 가짜 크레덴셜이 그대로 들어 있다. 각 실행의 `summary.json` 에 경로가 적혀 있다.
