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

## 품질 검사 (훅)
- 커밋 전 검사: `.scripts/pre-commit.sh`
- 커밋 후 검사: `.scripts/post-commit.sh`
- 작업 "완료" 전 전체 검증: `.scripts/verify.sh` (위 두 스크립트 + 경계 검사 실행)
- 이 스크립트들은 설문에서 고른 프리셋(린트·포맷·테스트 등)으로 생성됩니다. 같은 검사를 LLM으로 대체하지 마세요.

## 절대 규칙 (항상 적용)
1. **요청한 범위만** 한다. 끼워넣기 리팩터링·가상의 미래 대비 설계 금지.
2. 기존 파일 수정을 새 파일 생성보다 우선한다.
3. 작업을 "완료"로 보고하기 전 반드시 `.scripts/verify.sh`를 통과시킨다.
4. **다음 경로는 절대 수정·커밋하지 않는다**: `{{FILL:dev.never_touch}}`
5. 되돌릴 수 없는 작업(push, 삭제, 배포, 머지)은 실행 전 사용자 확인.
6. 같은 실수가 반복되면 개별 수정 대신 **그것을 막는 규칙/검사를 환경에 추가**한다.

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
