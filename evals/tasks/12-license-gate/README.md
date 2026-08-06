# 12 · 라이선스 게이트 (vertical-workflow · hard)

**질의**: POLICY.md 의 라이선스 정책을 구현한 `check_licenses.py` CLI 를 작성하라.
패키지당 `이름<TAB>allow|deny<TAB>사유` 한 줄, 이름 오름차순, deny 존재 시 exit 1.

**함정 구조** (설계 원칙 ①② — 계약 엄격함·엣지 데이터, 기만 없음):

1. **식 파싱이 진짜 작업** — 보이는 deps.json·테스트는 단일 식별자 위주라 문자열 매칭으로도
   통과한다. held-out 은 `((MIT OR (GPL-2.0-only AND UNKNOWN-1.0)) AND (BSD-2-Clause OR
   AGPL-3.0-only))` 같은 중첩 괄호와, 괄호 없는 결합 우선순위(`WITH` > `AND` > `OR` —
   `MIT OR GPL-3.0-only AND UNKNOWN-1.0` 은 allow)를 찌른다. 재귀 하강 파서 없이는 못 버틴다.
2. **deny 사유의 결정론** — deny 는 한 값이 아니라 세 사유(forbidden/conditional/unknown)로
   갈리고, 혼합 시 우선순위(§7)가 정의돼 있다. `UNKNOWN-1.0 OR LGPL-3.0-only` 는
   `conditional`, `LGPL AND GPL` 은 `forbidden`. LGPL 이 "조건부지만 판정은 deny" 라는
   비대칭도 정책 §3 에만 있다.
3. **관용과 실패의 경계** — 식별자·연산자 대소문자 무시(§8)는 관용이지만, 파싱 불가
   (`MIT AND`, 괄호 불일치, 빈 식, license 누락·비문자열)는 예외가 아니라 `deny unknown`
   이어야 한다(§4). 크래시하면 출력 자체가 깨져 전 그룹이 떨어진다.

**왜 이 태스크인가**: 규칙 하나하나는 명확하지만 전부 지켜야 출력이 바이트 단위로 맞는다.
쉬운 테스트에서 멈추는 실행(0.15)과 문법·의미론·형식 계약을 전부 구현한 실행(1.00)이 갈린다.

**채점**: gate 0.15(기본 4종) + 중첩식 0.20 + WITH·우선순위 0.20 + 어휘·오류 0.15 +
exit code 0.15 + 형식·정렬 0.15. 기대 출력은 골든 CLI 로 산출해
`solution/heldout/*.expected.tsv` 에 하드코딩(재생성: `gen_expected.py`).
