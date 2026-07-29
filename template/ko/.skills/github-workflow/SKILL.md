---
name: github-workflow
description: Git/GitHub 작업 규칙. 브랜치 생성, 스테이징, 커밋, 푸시, PR 생성·리뷰, 이슈 처리 등 버전 관리와 협업 작업을 할 때 사용한다.
---

# Git / GitHub

> 보호 브랜치 **{{FILL:gh.default_branch}}** · 커밋 컨벤션 **{{FILL:gh.commit_convention}}**({{FILL:gh.commit_language}}) · 브랜치 규칙 **{{FILL:gh.branch_naming}}**
> GitHub 작업은 `gh` CLI 를 쓴다.

## git 에서만 적용되는 금지 사항
`AGENT.md` 의 규칙(되돌릴 수 없는 작업 확인, 우회 플래그 금지)에 더해:

- **커밋·푸시는 명시 요청이 있을 때만** 한다. 코드를 고쳤다고 자동으로 커밋하지 않는다.
- `{{FILL:gh.default_branch}}` 에 force push 하지 않는다. 요청받아도 경고부터 한다.
- amend 대신 **새 커밋**을 쌓는다(사용자가 amend 를 명시 요청한 경우 제외). 훅 실패 뒤 amend 는 직전 커밋을 손상시킬 수 있다.
- git config 를 바꾸지 않는다.

## 스테이징
`git add -A` / `git add .` 대신 **파일을 이름으로 명시**한다. 시크릿·대용량 바이너리가 섞여 들어가는 사고는
거의 전부 이 한 줄에서 나온다. `{{FILL:dev.never_touch}}` 는 스테이징 대상이 아니다.

커밋 전에 상태를 본다: `git status` · `git diff` · `git log --oneline -10`(이 레포의 커밋 스타일 파악).

## 커밋 메시지
`{{FILL:gh.commit_convention}}` 컨벤션, `{{FILL:gh.commit_language}}` 로 작성한다.
conventional 이면 `type(scope): subject` — `feat`·`fix`·`refactor`·`test`·`docs`·`chore`.

**무엇보다 왜**를 1~2문장으로. 제목 70자 이하, 상세는 본문. 실제 diff 를 반영하고 하지 않은 일을 적지 않는다.

```bash
git commit -m "$(cat <<'MSG'
fix(payments): 멱등키 만료 전 재시도하도록 수정

Stripe 멱등키가 24h만 유지되어 그 이후 재시도 시 중복 청구가 발생했다.
재시도 윈도우를 23h로 제한해 방지한다.
MSG
)"
```

## PR
- 만들기 전에 **전체 커밋 범위**를 본다: `git diff {{FILL:gh.default_branch}}...HEAD`. 최신 커밋만 보고 쓰지 않는다.
- 제목 70자 이하. 본문은 `## Summary` + `## Test plan`(체크리스트).
- 본문은 HEREDOC 으로 넘긴다. 완료 후 **PR URL 을 반환**한다.
- PR·이슈는 전체 URL 마크다운 링크로 적는다. 맨 `#123` 금지.

## 예상 못 한 상태
머지 충돌은 한쪽을 버리지 말고 해결한다. 모르는 파일·브랜치·잠금 파일은 지우거나 덮어쓰기 전에
무엇인지 확인한다 — 사용자의 진행 중 작업일 수 있다.
