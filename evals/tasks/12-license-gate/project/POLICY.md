# 오픈소스 라이선스 정책 (SPDX 식 판정 규칙)

이 문서가 라이선스 판정의 유일한 스펙이다. 의존성의 `license` 필드는 SPDX 라이선스
식(expression)이며, 아래 규칙으로 패키지마다 `allow` 또는 `deny` 를 판정한다.

## 1. 허용 라이선스 (allow)

`MIT` · `BSD-2-Clause` · `BSD-3-Clause` · `Apache-2.0` · `ISC`

## 2. 금지 라이선스 (deny, 사유 `forbidden`)

GPL·AGPL 계열 전부:

`GPL-2.0-only` · `GPL-2.0-or-later` · `GPL-3.0-only` · `GPL-3.0-or-later` ·
`AGPL-3.0-only` · `AGPL-3.0-or-later`

구식 표기도 동일 취급: `GPL-2.0` · `GPL-2.0+` · `GPL-3.0` · `GPL-3.0+` · `AGPL-3.0`

## 3. 조건부 라이선스 (deny, 사유 `conditional`)

LGPL 계열은 법무 검토 전까지 정책상 **deny 로 판정하되 사유에 `conditional` 을 명시**한다:

`LGPL-2.1-only` · `LGPL-2.1-or-later` · `LGPL-3.0-only` · `LGPL-3.0-or-later`
(구식 표기 `LGPL-2.1` · `LGPL-2.1+` · `LGPL-3.0` · `LGPL-3.0+` 포함)

## 4. 알 수 없는 식별자 (deny, 사유 `unknown`)

위 1~3절 어디에도 없는 식별자, `license` 필드 누락·비문자열, 빈 식,
그리고 **파싱할 수 없는 식**(괄호 불일치·연산자 위치 오류 등)은 전부 deny 사유 `unknown`.

## 5. `WITH` (예외 조항)

`<라이선스> WITH <예외>` 는 **기반 라이선스 기준**으로 판정한다.
- `Apache-2.0 WITH LLVM-exception` → `Apache-2.0` 으로 판정 → allow
- `GPL-2.0-only WITH Classpath-exception-2.0` → `GPL-2.0-only` 로 판정 → deny(forbidden)

## 6. `OR` / `AND`

- `A OR B`: 피연산자 중 **하나라도 allow 면 allow** (선택 가능한 라이선스이므로).
- `A AND B`: 피연산자가 **전부 allow 여야 allow**.
- 괄호로 중첩할 수 있다. 괄호가 없으면 결합 우선순위는 `WITH` > `AND` > `OR`.

## 7. deny 사유의 우선순위

식 전체가 deny 로 판정될 때, deny 인 부분식의 사유가 여러 종류면
`forbidden` > `conditional` > `unknown` 순서로 **가장 앞선 사유 하나**를 보고한다.
- `LGPL-2.1-only AND GPL-2.0-only` → deny, 사유 `forbidden`
- `UNKNOWN-1.0 OR LGPL-3.0-only` → deny, 사유 `conditional`

## 8. 표기 관용

- 식별자·연산자(`AND`/`OR`/`WITH`) 모두 **대소문자 무시** (`mit`, `and` 허용).
- 토큰 사이 공백은 몇 칸이든 허용. 괄호와 토큰 사이 공백 유무도 무관.

## 9. 판정 사유 어휘

출력의 사유(reason)는 다음 네 값만 쓴다:

| 판정 | 사유 |
|---|---|
| allow | `ok` |
| deny (금지 라이선스) | `forbidden` |
| deny (LGPL 조건부) | `conditional` |
| deny (알 수 없음·파싱 불가) | `unknown` |
