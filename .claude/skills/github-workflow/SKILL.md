---
name: github-workflow
description: Git/GitHub 작업 규칙. 브랜치 생성, 스테이징, 커밋, 푸시, PR 생성·리뷰, 이슈 처리 등 버전 관리와 협업 작업을 할 때 사용한다.
---

# 깃허브 작업 규칙 (Git / GitHub Workflow)

> 버전 관리와 협업 작업에 따른다. GitHub 작업은 `gh` CLI를 쓴다. IMPORTANT: 시스템/사용자 메시지가 이 스킬보다 우선한다.
> 보호 브랜치: main · 커밋 컨벤션: Conventional Commits (한국어) · 브랜치 규칙: feature/<설명>, fix/<설명>

## 0. 안전 수칙 (절대 규칙)
- **명시 요청 없이 커밋하지 않는다.** "커밋해줘"가 있을 때만.
- **명시 요청 없이 push 하지 않는다.**
- git config를 수정하지 않는다.
- 파괴적 명령은 사용자가 명시 요청할 때만: `push --force`, `reset --hard`, `checkout .`, `clean -f`, `branch -D`.
- `main`에 force push 금지. 요청받아도 경고한다.
- 훅을 건너뛰지 않는다(`--no-verify`, `--no-gpg-sign` 금지). 훅 실패는 우회하지 말고 원인을 고친다.
- amend 대신 항상 **새 커밋**(사용자가 amend를 명시 요청한 경우 제외). 훅 실패 후 amend하면 직전 커밋이 손상될 수 있다.
- `.env, secrets/, .venv/, node_modules/` 경로와 시크릿(.env, credentials)을 스테이징하지 않는다.

## 1. 커밋 전 (병렬 실행으로 상태 파악)
- `git status` — 변경/미추적 확인 (`-uall`은 큰 레포에서 메모리 문제, 쓰지 않는다)
- `git diff` — 스테이징/비스테이징 변경
- `git log --oneline -10` — 이 레포의 커밋 스타일 파악

## 2. 스테이징
- `git add -A`/`git add .` 대신 **파일을 이름으로 명시**. 시크릿·대용량 바이너리 혼입 사고를 막는다.
- 시크릿 의심 파일은 커밋하지 않는다. 명시 요청 시 경고한다.

## 3. 커밋 메시지
- 컨벤션: **Conventional Commits** / 언어: **한국어**.
- conventional이면 `type(scope): subject` 형식. type: `feat`(새 기능), `fix`(버그), `refactor`, `test`, `docs`, `chore`.
- **무엇보다 왜**를 1~2문장으로. 제목 줄 70자 이하, 상세는 본문.
- 실제 diff를 반영한다. 하지 않은 일을 지어내지 않는다.
- HEREDOC으로 메시지를 전달해 포맷을 보존한다.

```bash
# conventional + 한국어 예시
git commit -m "$(cat <<'EOF'
fix(payments): 멱등키 만료 전 재시도하도록 수정

Stripe 멱등키가 24h만 유지되어 그 이후 재시도 시 중복 청구가 발생했다.
재시도 윈도우를 23h로 제한해 방지한다.
EOF
)"
```

## 4. PR
- 생성 전 base로부터 **전체 커밋 범위**를 본다: `git log` + `git diff main...HEAD` (최신 커밋만 보지 말 것).
- 제목 70자 이하. 본문은 `## Summary` + `## Test plan`(체크리스트).
- `gh pr create`에 HEREDOC으로 본문 전달. 완료 후 **PR URL을 반환**한다.
- PR/이슈는 항상 전체 URL 마크다운 링크로 표기. 맨 `#123` 금지.
- base 브랜치: `main`.

## 5. 충돌·예상 못 한 상태
- 머지 충돌은 변경을 버리지 말고 해결한다.
- 익숙지 않은 파일·브랜치·잠금 파일은 삭제·덮어쓰기 전에 조사한다(사용자의 진행 중 작업일 수 있다).

## 6. gh CLI
- 이슈/PR/체크/릴리스 등 모든 GitHub 작업에 `gh`. URL을 받으면 `gh`로 조회.
- PR 코멘트: `gh api repos/{owner}/{repo}/pulls/{n}/comments`.

## 체크리스트
- [ ] 사용자가 커밋/푸시를 명시 요청했는가
- [ ] 파일을 이름으로 명시해 스테이징했는가(시크릿·never_touch 미포함)
- [ ] 커밋이 Conventional Commits 컨벤션과 한국어 언어를 따르고 "왜"를 설명하는가
- [ ] PR이 전체 커밋 범위를 반영하는가
- [ ] 훅 우회·파괴적 명령 무단 실행이 없는가
- [ ] PR/이슈를 전체 URL 링크로 표기했는가
