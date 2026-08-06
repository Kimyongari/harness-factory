# 09 · 릴리스 노트 (office-comm · medium)

**질의**: commits.jsonl 의 커밋 40개에서 CHANGELOG.md 맨 위에 0.5.0 절을 규칙 6개
(형식·feat/fix 만·revert 쌍 제외·BREAKING 재분류·이슈번호 유지·오름차순)대로 추가하라.

**함정 구조** (설계 원칙 ①: 엄격한 산출물 계약):

- **revert 쌍 3세트** — 원 커밋(feat #21·#36, fix #29)과 revert 커밋을 둘 다 빼야 한다.
  subject 만 훑으면 원 커밋은 멀쩡한 feat/fix 로 보인다. revert 커밋은 body 의
  "This reverts commit <sha>" 로만 원 커밋과 이어진다.
- **BREAKING 재분류 2건** — feat #31 과 fix #44 는 body 에만 BREAKING: 마커가 있다.
  subject 분류(feat→Added)를 기계적으로 적용하면 Breaking 절이 비고 Added/Fixed 에
  중복 수록된다. 채점은 "Breaking 절 = 정확히 {#31, #44}" 를 본다.
- **내부 변경 19건** — chore/refactor/test 14 + docs 5. 성실하게 다 옮겨 적는 실행이
  정밀도(0.3)에서 떨어진다. 포함 대상은 15건뿐이다.
- **순서 계약** — 하위 절 순서(Breaking→Added→Fixed)와 절 안 이슈번호 오름차순.
  커밋 파일 순서대로 나열하면 어긋난다.

**채점 방식**: 0.5.0 절만 절 단위 정규식으로 잘라, 이슈번호 토큰(#N)으로 재현율(0.3)·
정밀도(0.3)를 재고, Breaking 분류(0.2)·형식/순서/0.4.0 보존(0.15)을 본다. 문장 품질은
재지 않는다 — 제외 대상 유입은 revert 이슈번호와 chore/docs 고유 키워드로 잡는다.

**왜 이 태스크인가**: Harness-Bench 실패 1위(계약/형식 위반 36.4%)의 문서 버전이다.
커밋을 눈에 띄는 대로 옮기면 재현율은 만점이지만 정밀도·분류·순서가 무너진다 —
"쓰기 쉬운 산출물"과 "계약을 지킨 산출물"이 갈린다.
