# 실행 결과 보관소

해석과 교훈 → **[`FINDINGS.md`](FINDINGS.md)** · 최신 수치 → **[`LATEST.md`](LATEST.md)**

| 폴더 | 최신 실행 |
|---|---|
| [`claude-code/`](claude-code/README.md) | 2026-08-05 · 스위트 v2(01-28) · opus-5 (effort high) |
| [`codex/`](codex/README.md) | 2026-07-29 · gpt-5.6-sol (reasoning high) |
| [`cursor/`](cursor/README.md) | 없음 (CLI 미설치) |

세 폴더 README는 같은 목차를 쓴다: 실행 설정 → 결과 → 실행 이력 → 주의사항 → 재현.

## 폴더 규약

실행 하나가 디렉터리 하나다: `<타깃>/<YYYYMMDD>-<모델>-<추론수준>-<범위>/`.
`abrun`은 결과를 이 디렉터리 루트에 `<타임스탬프>-<모드>/`로 만드니, 끝나면 타깃 폴더로
옮기고 규약대로 이름을 붙인 뒤 그 README 이력 표에 한 줄 적는다.

| 파일 | 내용 |
|---|---|
| `summary.json` | 원시 데이터(점수, 항목별 판정, 토큰, 시간, 하네스 커밋 SHA) |
| `scorecard.md` | 사람이 읽는 요약 (`python -m evals.scorecard` 생성) |

## 모드

| 모드 | 기대 | 용도 |
|---|---|---|
| `golden` | 전부 1.00 | 정답을 오답 처리하지 않는가 |
| `baseline` | 전부 ≤ 0.15 | 미수행을 통과시키지 않는가 |
| `agent` | 측정값 | 실제 A/B |

앞의 둘이 기대를 벗어난 상태의 `agent` 결과는 읽지 않는다. LLM을 호출하지 않으므로
CI(`python -m evals.run`)에서 항상 돈다.

## 비교 시 주의

- 채점기·하네스 버전이 실행마다 다르다. 각 README의 설정 표를 먼저 확인한다.
- PR [#24](https://github.com/Kimyongari/harness-factory/pull/24) 이전 실행은 커밋 게이트 편향의 영향을 받는다([`codex/README.md`](codex/README.md) 보정 열).
- 비용 지표는 도구마다 노출 범위가 다르다(Codex는 `cost_usd`와 턴 수 없음).

## 트랜스크립트

작업공간과 트랜스크립트는 레포 밖 `EVAL_WORKROOT`에 남는다. 용량이 크고 픽스처의
가짜 크레덴셜이 들어 있어서 커밋하지 않는다. 경로는 각 `summary.json`에 적혀 있다.

## 스위트 버전 주의

2026-08-06 스위트 v3 도입으로 **v2 태스크 정의(`evals/tasks/`)가 삭제**됐다. 그 전
실행 결과의 `--regrade`·스코어카드 재생성은 태스크 정의가 필요하므로, PR #34 머지
시점 이전 커밋을 체크아웃해서 돌려야 한다. 커밋된 `summary.json`·`scorecard.md` 는
그대로 유효하다.
