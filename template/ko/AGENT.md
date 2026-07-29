# AGENT.md

<!-- 이 파일은 모든 요청에 로드된다. 여기 있는 토큰은 매번 지불하는 비용이다. -->
<!-- 넣지 않는 것: 파일을 보면 아는 사실, 일반적인 좋은 개발 습관, 훅의 내부 동작. -->
<!-- 넣는 것: 이 레포에서만 참인 것, 어겼을 때 되돌리기 어려운 것, 어디를 볼지. -->

## 프로젝트
**{{FILL:project.name}}** — {{FILL:project.description}}
{{FILL:project.language}} {{FILL:project.language_version}} · {{FILL:project.framework}} · {{FILL:project.package_manager}}

| 목적 | 명령 |
|---|---|
| 설치 | `{{FILL:dev.install_cmd}}` |
| 실행 | `{{FILL:dev.run_cmd}}` |
| 검증 | `.scripts/verify.sh` — **이게 "완료"의 정의다** |

## 이 레포의 함정
{{FILL:dev.gotchas}}

## 지켜야 하는 것
1. `.scripts/verify.sh` 를 통과시킨 뒤에 "완료"라고 말한다. 통과 못 했으면 그 사실을 말한다.
2. `{{FILL:dev.never_touch}}` 는 읽지도, 쓰지도, 커밋하지도 않는다.
3. 되돌릴 수 없는 작업(push·삭제·배포·머지)은 실행 전에 사용자 확인을 받는다.
4. 검사가 막으면 **원인을 고친다.** 우회 플래그(`--no-verify` 등)로 통과시키지 않는다.
5. 같은 실수가 두 번 나오면, 그 실수를 막는 검사를 환경에 추가한다.

위 검사들은 프롬프트가 아니라 **런타임 훅**이 결정론적으로 실행한다 — 잊어도 작동하고, 설득으로 끌 수 없다.
어떤 훅이 언제 도는지는 `.docs/references/harness.md`.
<!--TARGET_ENFORCEMENT-->

## 어디를 볼지
| 상황 | 문서 |
|---|---|
| 코딩·디버깅·리팩터링 | `.skills/development/SKILL.md` |
| 커밋·PR·브랜치 | `.skills/github-workflow/SKILL.md` |
| 문서·README·요약 작성 | `.skills/doc-writing/SKILL.md` |
| 웹 조사·사실 확인 | `.skills/web-research/SKILL.md` |
| 설계 신념·아키텍처 경계 | `.docs/design/` |
| 명세 · 진행 중 작업 · 기술부채 | `.docs/specs/` · `PLAN.md` · `.docs/plans/tech-debt.md` |
| 무엇을 볼지 모를 때 | `.docs/index.md` |

여러 단계에 걸친 작업의 결정은 `PLAN.md` 에 적는다. 컨텍스트 압축은 손실이 있어서,
기억에 의존한 결정은 사라진다.
