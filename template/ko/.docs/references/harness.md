# 하네스 참조 — 어떤 검사가 언제 도는가

이 문서는 **하네스를 디버깅하거나 바꿀 때만** 읽으면 된다. 평소 작업에는 필요 없다 —
검사는 런타임이 알아서 발동하고, 실패하면 무엇을 고쳐야 하는지 출력에 나온다.

## 런타임 훅

| 시점 | 스크립트 | 역할 |
|---|---|---|
| 모든 셸 명령 직전 | `.scripts/guard-bash.sh` | `rm -rf`·force push·`--no-verify`·파이프-투-셸(`curl\|sh`)·권한 상승(`sudo`/`chmod 777`)·never_touch 경로 쓰기·스테이징 차단 |
| 파일 수정 직후 | `.scripts/pre-commit.sh` | 설문에서 고른 린트/포맷/타입체크 |
| 모든 도구 호출 직후 | `.scripts/trace.sh` | 도구 호출 궤적을 `.trace/tools.jsonl` 에 기록(커밋 안 됨) — 실패 원인 분석용 |
| 세션 시작·재개·압축 후 | `.scripts/session-context.sh` | 브랜치·미커밋 변경·`PLAN.md` 포인터를 다시 주입 |
| 컨텍스트 압축 직전 | `.scripts/precompact-note.sh` | 압축은 손실이 있으니 상태를 `PLAN.md` 에 남기라고 상기 |
| "완료" 보고 직전 | `.scripts/verify.sh` | `check-boundaries.sh` → `pre-commit.sh` → `post-commit.sh` 순서 실행 |
| 커밋 후 | `.scripts/post-commit.sh` | 무거운 검사(보통 테스트) |
| 경계 검사 | `.scripts/check-boundaries.sh` | `.docs/design/architecture.md` 의 레이어 순서 기준 역방향 import 탐지 |

이 검사들을 LLM 으로 다시 구현하지 마라. 스크립트가 단일 진실 공급원이다.

## 도구 무관 백스톱 — git 훅

런타임 훅은 도구마다 다르지만 git 훅은 `git commit` / `git push` 시점에 발동하므로
**어떤 에이전트가 커밋하든** 동일하게 적용된다. 클론마다 1회 설치:

```
git config core.hooksPath .githooks
```

- `.githooks/pre-commit` — `check-boundaries.sh` + `pre-commit.sh`
- `.githooks/pre-push` — 보호 브랜치(`{{FILL:gh.default_branch}}`)로의 강제 푸시 거부 + `post-commit.sh`

## 검사를 바꾸고 싶을 때

| 바꿀 것 | 고칠 파일 |
|---|---|
| 어떤 린트·테스트가 도는지 | `.scripts/pre-commit.sh` · `.scripts/post-commit.sh` |
| 무엇을 차단할지 | `.scripts/guard-bash.sh` (규칙을 늘리려면 이 파일) |
| 레이어 경계 | `.docs/design/architecture.md` 의 허용 방향 |
| 도구 권한·훅 배선 | `.agents/agent.yaml` |
