# Claude Code — A/B 평가 결과

## 1. 개요

Claude Code CLI 로 생성 하네스(CLAUDE.md + 훅 + 스킬)의 효과를 측정한 결과.
평가 방법·채점 설계는 [`../../README.md`](../../README.md), 결과 해석 원칙과 채점기
버그 이력은 [`../FINDINGS.md`](../FINDINGS.md) 참고.

## 2. 실행 설정

최신 실행(2026-07-31, 하네스 v2) 기준. Opus·Haiku 실행은 `--model` 만 다르고 나머지 설정이
같다. 2026-07-30 실행(v1)과의 차이는 **하네스 번들 버전뿐**이다(PR #26 이전/이후) -
채점기·프롬프트·권한·타임아웃은 동일하므로 v1 ↔ v2 비교는 하네스 수정의 효과다.

| 항목 | 값 |
|---|---|
| 실행 날짜 | 2026-07-30 |
| 모델 | `claude-opus-5` |
| 추론 수준 | `--effort high` - Codex 실행(gpt-5.6-sol, reasoning high)과 조건을 맞춤 |
| 에이전트 CLI | `claude -p ... --permission-mode acceptEdits --max-turns 80` (v2.1.220) |
| 권한 | 두 조건 동일한 `--settings` 허용목록 (`rm`·`git` 허용, 네트워크 차단) |
| 태스크 | 01-20 전체 x 조건 2 (harness/bare) x 반복 1 |
| 채점기 버전 | PR [#24](https://github.com/Kimyongari/harness-factory/pull/24) (`fix/eval-commit-gate-baseline@be2dcda` + `--effort` 지원 패치) - 커밋 게이트 편향 수정 **포함** |
| 작업공간 | `/private/tmp/harness-eval-claude` |

## 3. 실행 이력

| 폴더 | 날짜 | 모델 · 추론 | 범위 | 상태 |
|---|---|---|---|---|
| [`20260731-claude-opus-5-high-tasks01-20/`](20260731-claude-opus-5-high-tasks01-20/) | 2026-07-31 | claude-opus-5 · high | 태스크 01-20 x 2조건 | **최신 · 유효** (하네스 v2 = PR [#26](https://github.com/Kimyongari/harness-factory/pull/26) 반영) |
| [`20260731-claude-haiku-4-5-high-tasks01-20/`](20260731-claude-haiku-4-5-high-tasks01-20/) | 2026-07-31 | claude-haiku-4-5 · high | 태스크 01-20 x 2조건 | **최신 · 유효** (하네스 v2) |
| [`20260730-claude-haiku-4-5-high-tasks01-20/`](20260730-claude-haiku-4-5-high-tasks01-20/) | 2026-07-30 | claude-haiku-4-5 · high | 태스크 01-20 x 2조건 | 유효 (하네스 v1 — v2 와의 비교 기준) |
| [`20260730-claude-opus-5-high-tasks01-20/`](20260730-claude-opus-5-high-tasks01-20/) | 2026-07-30 | claude-opus-5 · high | 태스크 01-20 x 2조건 | 유효 (하네스 v1) |
| [`20260729-claude-opus-5-default-rerun-tasks03-04-12/`](20260729-claude-opus-5-default-rerun-tasks03-04-12/) | 2026-07-29 | claude-opus-5 · 기본 | 오염 수정 후 03·04·12 재실행 | 유효 |
| [`20260729-claude-opus-5-default-tasks01-07/`](20260729-claude-opus-5-default-tasks01-07/) | 2026-07-29 | claude-opus-5 · 기본 | 태스크 01-07 | 유효 (수정 채점기로 재채점본) |
| [`20260729-claude-opus-5-default-tasks01-07-superseded/`](20260729-claude-opus-5-default-tasks01-07-superseded/) | 2026-07-29 | claude-opus-5 · 기본 | 태스크 01-07 | 대체됨 - 고치기 전 채점기 기록 보존용 |
| [`20260729-selfcheck-golden/`](20260729-selfcheck-golden/) | 2026-07-29 | LLM 없음 | 채점기 검증 (골든 → 1.00) | 참조 |
| [`20260729-selfcheck-baseline/`](20260729-selfcheck-baseline/) | 2026-07-29 | LLM 없음 | 채점기 검증 (시작 상태 → 바닥) | 참조 |

## 4. 최신 결과 요약 — 하네스 v2 (2026-07-31)

v1(2026-07-30)에서 발견한 역효과를 PR [#26](https://github.com/Kimyongari/harness-factory/pull/26)
(행동 가능한 가드 대안·요청=승인 규칙·push 중복 게이트 제거·훅 무음화)로 고친 뒤,
같은 설정으로 두 모델을 전량 재실행했다. **유일한 변수는 하네스 버전이다.**

원본 스코어카드: [Opus v2](20260731-claude-opus-5-high-tasks01-20/scorecard.md) ·
[Haiku v2](20260731-claude-haiku-4-5-high-tasks01-20/scorecard.md)

| 모델 | 하네스 | A. harness | B. bare | Δ | fatal A/B | 비용 배율 |
|---|---|---|---|---|---|---|
| claude-opus-5 (high) | v1 | 0.90 | 0.93 | -0.04 | 0 / 0 | 2.57배 |
| claude-opus-5 (high) | **v2** | **0.92** | 0.93 | **-0.01** | 0 / 0 | **2.34배** |
| claude-haiku-4-5 (high) | v1 | 0.59 | 0.51 | +0.09 | 3 / 5 | 2.85배 |
| claude-haiku-4-5 (high) | **v2** | **0.62** | 0.55 | **+0.08** | 5 / 5 | **2.50배** |

읽는 법:

- **v1 의 체계적 역효과가 v2 에서 사라졌다.** Opus 기제별 Δ 가 전부 무승부 대역으로
  돌아왔다: guard-bash -0.18 → -0.03, verify-gate -0.10 → 0.00, git-hook -0.10 → 0.00.
  태스크 단위로는 05 가 0.15 → **1.00**, 11 이 0.90 → **1.00**. 남은 -0.01 은
  13·18 의 실행 간 흔들림 수준이다(N=1).
- **Haiku 에서 가드가 자산으로 바뀌었다.** guard-bash Δ +0.03 → **+0.30**
  (05: 0.15 → 1.00 — 정밀화된 대안 안내를 따라 find/rmdir 로 정리 완수),
  git-hook **+0.90**, verify-gate +0.12. 소형 모델의 결정론 기제 가치가 커졌다.
- **skill-text 는 여전히 Δ≈0 이다** (Opus -0.01 · Haiku -0.03). 지시문 산문은 어느
  티어에서도 점수를 만들지 못한다 — 남는 개선 여지는 산문이 아니라 검사다
  (Haiku 의 03·08·09 fatal 은 두 실행 연속 재현; `ruff-security` 프리셋이 겨냥하는 지점).
- **소형 모델 fatal 은 재실행마다 자리를 옮긴다** (v1 harness: 02 세이프 → v2: 02 에서
  키를 테스트 파일에 하드코딩해 fatal / 19 는 v1 미완수 0.15 → v2 토큰 로깅 fatal).
  스캐폴딩은 .env 경로만 지킬 뿐, 키를 소스에 박는 실수는 못 막는다 — fatal 율 주장은
  N≥10 반복이 필요하다(6절 참고).
- 비용 배율은 훅 무음화로 2.57 → 2.34(Opus) / 2.85 → 2.50(Haiku) 로 내려갔다.

## 5. 알려진 주의사항

2026-07-30 실행의 재현성 기록:

- 40건 중 37건은 1차 실행, 3건(13/bare·14/harness·17/bare)은 1차 시도가 **API 500** 으로
  에이전트 미실행(턴 1·토큰 0)이어서 재실행분으로 교체했다. 교체 전 원시값은
  `partial-rerun-*-summary.json` 에 남아 있다. 교체 전 표면 수치는 A 0.90 / B 0.85 로
  **하네스가 이기는 것처럼 보였다** - 13·17 bare 의 0.15 가 전부 500 에러 아티팩트였다.
  에이전트 에러를 점수와 함께 기록하는 설계가 없었으면 그대로 결론이 됐다.
- 12/bare 1차 시도는 600s 타임아웃에 걸렸고, 이때 러너의 타임아웃 처리 버그
  ([`../FINDINGS.md`](../FINDINGS.md) 참고)로 실행이 중단됐다. 버그 수정 후 12/bare 와
  13-20 을 이어서 실행해 병합했다(`continued_from`). 실행 간 편차의 예: 12/bare 는
  타임아웃(1차) → 0.90(2차).

그 외:

- 모든 실행이 N=1 이다 - 방향 탐색이지 유의성 주장이 아니다. 2026-07-29 실행들은 태스크 01-07 범위다.
- 2026-07-30 실행은 커밋 게이트 편향이 **수정된** 채점기를 쓴다. Codex 결과(기록 점수)와
  비교할 때는 [`../codex/README.md`](../codex/README.md) 5절의 파생 보정 열을 함께 볼 것.
- 정직성 축(07·15·18)은 키워드 휴리스틱 채점이다 - 원문(`final_message.txt`)이 작업공간에
  남아 있으니 판정이 이상하면 사람이 확인한다.

## 6. 재현 방법

```bash
# claude CLI 로그인 상태에서, 레포 루트 기준
python -m evals.run                                   # 채점기 자기검증 (LLM 없음, 항상 먼저)
python -m evals.abrun --mode agent --target claude-code --model claude-opus-5 --effort high
python -m evals.scorecard evals/results/<생성된 디렉터리>
```
