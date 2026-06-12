# eval 하니스 — 생성된 하네스가 에이전트를 잘 조종하는가

`tests/test_engine.py` 는 생성기(engine)의 단위테스트로, 산출물의 **모양**(CLAUDE.md 위치,
훅 설정 키, zip 권한 등)만 본다. 이 디렉터리는 한 단계 더 나아가, 생성된 산출물을 임시
프로젝트에 실제로 깔고 하네스가 에이전트 런타임을 어떻게 **조종**하는지 행동으로 측정한다.

[Anthropic — Writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
가 권하는 "현실적 멀티스텝 과제로 경험적 평가" 를 작은 규모로 구현한 것이다.

## 무엇을 측정하나

| 코드 | 측정 | 모드 |
|---|---|---|
| (b) | guard-bash 가 위반 명령(`rm -rf`, force push, never_touch 스테이징, 파이프-투-셸)을 차단하고 benign 은 통과시키는 **차단 정확도** | 경량 |
| (c) | verify.sh **Stop 게이트**가 망가진 상태를 막고(non-zero) 골든 수정 후엔 통과시키는 **게이트 정확도** | 경량 |
| (a) | 실제 에이전트가 골든 태스크를 프롬프트만 받고 풀어 verify.sh 를 통과시키는 **골든패스 통과율** | 전체 |

## 경량(light) vs 전체(full) 모드

- **경량 모드**: LLM 을 호출하지 않는다. guard-bash 에 PreToolUse JSON 을 흘려보내고,
  골든 프로젝트를 망가진/고친 두 상태로 verify.sh 에 태운다. 결정론적이라 CI 에서 항상 돈다.
- **전체 모드**: 실제 `claude -p` 헤드리스 에이전트를 골든 프로젝트에서 구동한 뒤 verify.sh
  결과로 통과 여부를 채점한다. 비싸고 비결정론적이라 환경변수로 게이트한다.

## 실행

```bash
# 경량 모드 스코어카드 (LLM 없음)
python -m evals.run

# 전체 모드 (실제 claude -p 구동)
HARNESS_EVAL_FULL=1 python -m evals.run --full

# 다른 에이전트로 교체 ({prompt} 가 치환됨)
HARNESS_EVAL_FULL=1 AGENT_CMD='codex exec {prompt}' python -m evals.run --full
```

CI 는 `pytest` 로 경량 모드를 함께 돈다(`tests/test_eval.py`). 전체 모드 테스트는
`HARNESS_EVAL_FULL=1` 이고 에이전트 CLI 가 PATH 에 있을 때만 실행되며, 그 외엔 skip 된다.

## 골든 태스크 추가하기

`evals/tasks/<id>/` 에 디렉터리를 만든다:

```
evals/tasks/<id>/
  task.yaml      # id, title, prompt(검증 가능한 목표 형태), gates
  project/       # 결함을 심은 시작 상태 — 임시 디렉터리로 복사된다
  solution/      # 골든 수정 파일 — 경량 모드에서 project/ 위에 덮어써 "푼 상태"를 모사
```

각 `project/` 는 망가진 상태에서 verify.sh 가 **실패**하고, `solution/` 을 덮으면 **통과**해야
한다. 모든 골든 프로젝트는 통과하는 테스트를 하나 이상 둬 post-commit(pytest, 빈 수집 시 exit 5)
단계가 골든 수정 후에 깔끔히 통과하도록 한다.
