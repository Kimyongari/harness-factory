# 15 · 멱등 DB 마이그레이션 (sre-devops · hard)

**질의**: users.email 을 contacts 테이블로 분리하는 migrate.py(up/down)를 계약대로 작성하라.

**함정 구조** (설계 원칙 ⑤ 멱등·가역성 + ① 산출물 계약):

- **멱등성** — 자연스러운 구현(CREATE TABLE + INSERT ... SELECT)은 두 번째 실행에서
  "table already exists" 로 죽거나 contacts 행을 중복 삽입한다. 상태 표식(user_version 등)이
  필요하다는 것을 스스로 검증해야 안다.
- **엣지 데이터** — NULL 이메일(행을 만들면 안 됨), 서로 다른 두 사용자의 동일 이메일
  (contacts.value 에 UNIQUE 를 걸고 싶은 유혹), 이름의 작은따옴표·큰따옴표·유니코드
  (문자열 포매팅 SQL 이 즉사).
- **롤백 무손실** — down 이 시드와 완전히 같은 users 를 복원해야 한다. 소실은 fatal.
- **호환성** — app.py 의 `SELECT name, email FROM users` 는 마이그레이션 후 죽는다.
  스키마만 옮기고 앱을 잊는 실행이 app_works 에서 떨어진다.

**채점 방식**: 에이전트의 작업공간 DB 상태는 보지 않는다. 채점기가 시드 원본으로 만든
깨끗한 임시 DB 에 작업공간의 migrate.py 를 up ×2 → 검사 → down → 검사 순으로 직접
실행한다 — 산출물(스크립트)의 성질 자체를 잰다 (Harness-Bench 의 DB 마이그레이션
오라클 방식).

**왜 이 태스크인가**: "up 한 번 돌아가면 완료" 로 보고하는 실행과, 계약의 네 성질
(멱등·무결성·무손실·호환)을 스스로 검증한 실행이 갈린다. verify 게이트 기제를 잰다.
