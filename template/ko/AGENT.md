# AGENT.md

<!-- 이 파일은 모든 세션에 들어간다. 보편적으로 적용되는 규칙만 둔다. -->
<!-- 안티패턴: 백과사전화. 모든 걸 넣으면 "다 중요 = 다 무시"가 된다. 500줄 이하 유지. -->
<!-- 상세는 작업별 문서/스킬로 분산하고, 여기서는 "찾는 법"만 알려준다(점진적 공개). -->

## 프로젝트
- 이름: {{FILL:project.name}}
- 설명: {{FILL:project.description}}
- 언어: {{FILL:project.language}} {{FILL:project.language_version}}
- 프레임워크: {{FILL:project.framework}} · 패키지매니저: {{FILL:project.package_manager}}
- 에이전트 역할: {{FILL:profile.role}} ({{FILL:profile.expertise}})

## 명령어 (결정론적 도구를 LLM으로 대체하지 말 것)
| 목적 | 명령 |
|---|---|
| 설치 | `{{FILL:dev.install_cmd}}` |
| 실행 | `{{FILL:dev.run_cmd}}` |

## 기계적 강제 (프롬프트 아님, 런타임)
아래 스크립트들은 Claude Code / Codex 런타임이 결정론적으로 호출한다. LLM이 "잊어도" 작동하므로 우회하지 마라.

| 시점 | 스크립트 | 역할 |
|---|---|---|
| 모든 `Bash` 호출 직전 | `.scripts/guard-bash.sh` | `rm -rf`, force push, `--no-verify`, never_touch 경로 쓰기를 차단 (PreToolUse) |
| `Edit` / `Write` / `MultiEdit` 직후 | `.scripts/pre-commit.sh` | 설문에서 고른 린트/포맷/타입체크 실행 (PostToolUse) |
| "완료" 보고 직전 | `.scripts/verify.sh` | `check-boundaries.sh` → `pre-commit.sh` → `post-commit.sh` 를 순서대로 실행, 실패 시 다음 행동 안내 (Stop) |
| 아키텍처 경계 검사 | `.scripts/check-boundaries.sh` | `dev.architecture_layers` 답변 기준 역방향 import 탐지 |
| 커밋 후 (보통 테스트) | `.scripts/post-commit.sh` | 무거운 검사 실행 |

Cursor: 스킬 규칙 `.cursor/rules/*.mdc` 는 코드/문서 파일에 `globs` 로 자동 첨부(LLM 판단 X), `00-overview.mdc` 는 `alwaysApply: true`.

이 검사들을 LLM으로 다시 구현하지 마라. 단일 진실 공급원이다.

## 절대 규칙 (항상 적용)
1. **구현 전에 가정을 드러낸다.** 요청에 대한 두 가지 해석이 모두 그럴듯하면 묵묵히 고르지 말고 둘 다 적어 묻는다. 더 단순한 길이 있으면 코드 짜기 전에 제안한다.
2. **요청한 범위만** 한다. 끼워넣기 리팩터링·가상의 미래 대비 설계 금지.
3. **작업을 "X 한다 → Y 로 검증" 형태로 다시 적는다.** 모호한 성공 기준("작동하게 해줘")은 매번 확인이 필요하다. 검증 가능한 목표로 변환 — `.skills/development/SKILL.md` 의 "목표 주도 실행" 참고.
4. 기존 파일 수정을 새 파일 생성보다 우선한다.
5. 작업을 "완료"로 보고하기 전 반드시 `.scripts/verify.sh`를 통과시킨다.
6. **다음 경로는 절대 수정·커밋하지 않는다**: `{{FILL:dev.never_touch}}` (`.scripts/guard-bash.sh` 가 추가로 차단).
7. 되돌릴 수 없는 작업(push, 삭제, 배포, 머지)은 실행 전 사용자 확인.
8. 같은 실수가 반복되면 개별 수정 대신 **그것을 막는 규칙/검사를 환경에 추가**한다.

## 무엇을 언제 읽을지 (점진적 공개 라우팅)
| 상황 | 읽을 곳 |
|---|---|
| 무슨 문서가 필요한지 모를 때 | `.docs/index.md` |
| 코딩/검증/리팩터링 | `.skills/development/SKILL.md` |
| 문서/README/주석/요약 작성 | `.skills/doc-writing/SKILL.md` |
| 웹 검색/사실 조사 | `.skills/web-research/SKILL.md` |
| 커밋/PR/브랜치 작업 | `.skills/github-workflow/SKILL.md` |
| 설계 신념·아키텍처 경계 | `.docs/design/` |
| 기능/API 명세 | `.docs/specs/` |
| 진행 중 작업·기술부채 | `.docs/plans/`, 루트 `PLAN.md` |
| 도구·권한·훅·검증 설정 | `.agents/agent.yaml` |

## 컨텍스트 위생 (context hygiene)
- 컨텍스트는 **선택적으로** 올린다. 관련 없는 문서를 미리 읽지 않는다.
- 멀티스텝 작업의 결정/상태는 컨텍스트의 "기억"에 의존하지 말고 `PLAN.md`에 **명시적으로 기록**한다. (단계가 길어지면 컨텍스트는 유실된다.)
- 검증 실패는 원인+수정법을 함께 읽고 스스로 고친다 → `.scripts/`.
- 판단이 애매하면 `.docs/design/core-beliefs.md`를 기준으로 결정한다.
