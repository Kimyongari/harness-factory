# Cursor A/B 평가 결과

## 1. 개요

Cursor(`cursor-agent`) 하네스의 A/B 실행 결과를 보관할 자리. 아직 에이전트 실행 이력이 없다.
`cursor-agent` CLI가 평가 머신에 설치되지 않았다. LLM 없이 도는 검증(가드 차단 정확도,
하네스 생성, 채점기 자기검증)은 Cursor 타깃에 대해서도 CI(`python -m evals.run`)가 매 커밋 측정한다.

## 2. 실행 설정

실행 시 적용될 설정(예정). 인자는 문서 기반이며 이 저장소에서 실측되지 않았다
([`abrun.py`](../../abrun.py)의 `verified=False` 표시 참고).

| 항목 | 값 |
|---|---|
| 실행 날짜 | - |
| 모델 | - |
| 추론 수준 | - |
| 에이전트 CLI | `cursor-agent -p ... --output-format stream-json --force` |
| 태스크 | 01-20 전체 x 조건 2 (harness/bare) |
| 채점기 버전 | 실행 시점의 커밋을 기록할 것 |
| 작업공간 | `EVAL_WORKROOT` 지정 |

## 3. 실행 이력

| 폴더 | 날짜 | 모델 · 추론 | 범위 | 상태 |
|---|---|---|---|---|
| (없음) | - | - | - | - |

## 4. 최신 결과 요약

실행 이력이 없다.

## 5. 알려진 주의사항

- 트랜스크립트 스키마를 실측하지 못했으므로, 프로세스·정직성 축 채점은 형식 무관
  추출기(`grading.bash_commands`)에 의존한다. 첫 실행 후 스키마를 확인할 것.
- 훅 차단 응답 형식이 Claude/Codex와 다르다(top-level `permission: deny`). 가드 정확도는
  CI가 Cursor 형식으로 별도 측정한다.

## 6. 재현 방법

```bash
# cursor-agent CLI 로그인 상태에서, 레포 루트 기준
python -m evals.run                                   # 채점기 자기검증 (LLM 없음, 항상 먼저)
python -m evals.abrun --mode agent --target cursor --model <모델>
python -m evals.scorecard evals/results/<생성된 디렉터리>
```
