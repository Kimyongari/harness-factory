# Claude Code A/B 평가 결과

측정 방법은 [`../../README.md`](../../README.md), 해석과 교훈은 [`../FINDINGS.md`](../FINDINGS.md).

## 1. 실행 설정 (v3 기준)

| 항목 | 값 |
|---|---|
| 모델 | `claude-opus-5` · `claude-haiku-4-5` (모델만 다르고 나머지 동일) |
| 추론 수준 | `--effort high` (Codex의 gpt-5.6-sol, reasoning high와 조건 일치) |
| CLI | `claude -p ... --permission-mode acceptEdits --max-turns 80` (v2.1.220) |
| 권한 | 양 조건 동일한 `--settings` 허용목록 (`rm`·`git` 허용, 네트워크 차단) |
| 범위 | 태스크 01-20 × 2조건 × 1회 (스위트 v2 실행은 01-28) |
| 하네스 | v3 = PR [#28](https://github.com/Kimyongari/harness-factory/pull/28)·[#29](https://github.com/Kimyongari/harness-factory/pull/29) 반영 |

v1 → v2 → v3의 유일한 변수는 하네스 버전이다(채점기·프롬프트·권한·타임아웃 동일).

## 2. 결과: 세 세대

| 모델 | 하네스 | harness | bare | Δ | fatal A/B | 비용 |
|---|---|---|---|---|---|---|
| opus-5 | v1 | 0.90 | 0.93 | -0.04 | 0 / 0 | 2.57배 |
| opus-5 | v2 | 0.92 | 0.93 | -0.01 | 0 / 0 | 2.34배 |
| opus-5 | **v3** | **0.93** | 0.94 | **-0.01** | 0 / 0 | 2.53배 |
| opus-5 | **v3 · 스위트 v2 (01-28)** | **0.94** | 0.94 | **+0.00** | 0 / 0 | 2.63배 |
| opus-5 | **v3 · 스위트 v3 (01-16 하드)** | **0.98** | 1.00 | **-0.01** | 0 / 0 | 1.88배 |
| haiku-4-5 | **v3 · 스위트 v3 (01-16 하드)** | **0.90** | 0.94 | **-0.04** | 0 / 0 | 1.58배 |
| haiku-4-5 | v1 | 0.59 | 0.51 | +0.09 | 3 / 5 | 2.85배 |
| haiku-4-5 | v2 | 0.62 | 0.55 | +0.08 | 5 / 5 | 2.50배 |
| haiku-4-5 | **v3** | **0.62** | 0.59 | **+0.03** | 4 / 5 | 2.79배 |

스코어카드: [Opus 스위트 v3](20260806-claude-opus-5-high-tasks01-16-suitev3/scorecard.md) ·
[Opus 스위트 v2](20260805-claude-opus-5-high-tasks01-28-suitev2/scorecard.md) ·
[Opus v3](20260731-claude-opus-5-high-tasks01-20-v3/scorecard.md) ·
[Haiku v3](20260731-claude-haiku-4-5-high-tasks01-20-v3/scorecard.md)

Opus는 v1→v3 단조 개선이다(0.90 → 0.93). 남은 -0.01은 N=1 흔들림이고, v1의 체계적
역효과(guard-bash -0.18)는 사라졌다. Haiku는 결정론 기제가 강하게 유지된다
(scaffold +0.85, git-hook +0.70, guard-bash +0.27). Haiku의 Δ 축소는 harness 하락이
아니라 bare 상승(0.55 → 0.59) 때문이다.

v3에서 발견한 역효과: Haiku 07이 1.00 → 0.15. `quick-tasks`(경량 모드)로 오분류해
"없는 함수" 함정을 조사 없이 통과시켰다. 상세는 [`../FINDINGS.md`](../FINDINGS.md).

스위트 v2(태스크 01-28, 새 축 8종 포함)에서 Opus는 완전 동률이다(0.94 / 0.94,
fatal 0/0). 태스크 단위 차이는 셋뿐: 12(+0.10, `.gitignore` 갱신), 28(+0.10, 머지
보류 결론), 22(-0.20, 오타 수정에 4줄 초과 변경). routine 축 5종만 떼면 비용 격차가
3.4배로 벌어진다 — 상세는 [`../FINDINGS.md`](../FINDINGS.md) 스위트 v2 절.

**스위트 v3(하드 16태스크)에서도 Opus 천장은 내려오지 않았다.** 완료(Completion) 32/32
만점, 조건 간 판정이 갈린 채점 항목 0개. 표의 0.98 vs 1.00 은 품질 차이가 아니라
Process 축의 토큰 효율 감점이다(예산 초과 5슬롯).

**같은 스위트를 Haiku 로 돌리자 변별이 살아났다** — 16태스크 중 6개에서 조건 차이(Opus 는
0개). 다만 방향이 나쁘다: `session-context` -0.43, `verify-gate` -0.20 으로 결정론적
기제가 손해를 냈다. 01·13 의 실패 방식이 같았다 — 프로젝트의 보이는 테스트가 초록이라
게이트가 완료를 승인했고, 계약 위반은 그대로 남았다. 대조군(06)이 +0.66 으로 흔들려
N=1 분산이 크다는 점도 함께 봐야 한다 — [`../FINDINGS.md`](../FINDINGS.md) Haiku 절.

## 3. 실행 이력

| 폴더 | 날짜 | 모델 · 하네스 | 상태 |
|---|---|---|---|
| [`20260807-...-haiku-4-5-...-suitev3/`](20260807-claude-haiku-4-5-high-tasks01-16-suitev3/) | 08-07 | haiku-4-5 · v3 · 스위트 v3 | **최신** (무효 0건) |
| [`20260806-...-opus-5-...-suitev3/`](20260806-claude-opus-5-high-tasks01-16-suitev3/) | 08-06 | opus-5 · v3 · 스위트 v3 | 유효 (무효 0건) |
| [`20260805-...-opus-5-...-suitev2/`](20260805-claude-opus-5-high-tasks01-28-suitev2/) | 08-05 | opus-5 · v3 · 스위트 v2 | 유효 (15슬롯 재실행·전량 재채점) |
| [`20260731-...-opus-5-...-v3/`](20260731-claude-opus-5-high-tasks01-20-v3/) | 07-31 | opus-5 · v3 | 유효 |
| [`20260731-...-haiku-4-5-...-v3/`](20260731-claude-haiku-4-5-high-tasks01-20-v3/) | 07-31 | haiku-4-5 · v3 | **최신** (9슬롯 재실행) |
| [`20260731-...-opus-5-.../`](20260731-claude-opus-5-high-tasks01-20/) | 07-31 | opus-5 · v2 | 유효 |
| [`20260731-...-haiku-4-5-.../`](20260731-claude-haiku-4-5-high-tasks01-20/) | 07-31 | haiku-4-5 · v2 | 유효 |
| [`20260730-...-opus-5-.../`](20260730-claude-opus-5-high-tasks01-20/) | 07-30 | opus-5 · v1 | 유효 |
| [`20260730-...-haiku-4-5-.../`](20260730-claude-haiku-4-5-high-tasks01-20/) | 07-30 | haiku-4-5 · v1 | 유효 |
| [`20260729-...-rerun-tasks03-04-12/`](20260729-claude-opus-5-default-rerun-tasks03-04-12/) | 07-29 | opus-5 · 기본 | 유효 |
| [`20260729-...-tasks01-07/`](20260729-claude-opus-5-default-tasks01-07/) | 07-29 | opus-5 · 기본 | 유효 (재채점본) |
| [`20260729-...-superseded/`](20260729-claude-opus-5-default-tasks01-07-superseded/) | 07-29 | opus-5 · 기본 | 대체됨 |
| [`20260729-selfcheck-golden/`](20260729-selfcheck-golden/) · [`-baseline/`](20260729-selfcheck-baseline/) | 07-29 | LLM 없음 | 참조 |

## 4. 주의사항

- 모든 실행이 N=1이다. Δ ±0.05는 편차 범위 안이다.
- 무효 슬롯 교체 이력: v2는 API 500 3건, v3(Haiku)은 세션 한도 9건, 스위트 v2(Opus)는
  529 폭풍 15건. 전부 재실행분으로 교체했고 원시값은 `partial-rerun-*.json`에 보존돼
  있다. 교체 전 수치는 결론이 반대였다([`../FINDINGS.md`](../FINDINGS.md) 실행 위생 절).
- 스위트 v2 실행은 채점기 경로 사고 1건(07 bare) 때문에 56슬롯 전체를 같은 채점기로
  재채점한 결과다(`regraded_from` 기록). 재채점 전 원본은 `pre-regrade-summary.json`.
- 정직성 축(07·15·18)은 키워드 휴리스틱이다. 원문(`final_message.txt`)이 작업공간에
  남으니 판정이 이상하면 사람이 읽는다.
- Codex 결과와 비교할 때는 [`../codex/README.md`](../codex/README.md)의 커밋 게이트
  보정 열을 함께 볼 것.

## 5. 재현

```bash
python -m evals.run                                   # 채점기 자기검증 (LLM 없음, 먼저)
python -m evals.abrun --mode agent --target claude-code --model claude-opus-5 --effort high
python -m evals.scorecard evals/results/<생성된 디렉터리>
```
