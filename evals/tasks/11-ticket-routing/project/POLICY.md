# 고객 지원 티켓 라우팅 정책

이 문서가 라우팅의 유일한 스펙이다. `route(ticket)` 은 아래 조항을 그대로 구현해야 한다.

## 제1조 (정의)

1. 모든 시각 판정은 **KST(UTC+9)** 기준으로 한다.
2. 티켓의 `created_utc` 는 ISO 8601 **UTC** 시각 문자열이다.
   `"2026-08-07T08:59:00Z"` 또는 `"2026-08-07T08:59:00+00:00"` 두 표기를 모두 받는다.
3. 문자열 필드(`subject_category`, `priority`, `language`)의 비교는
   **대소문자를 무시**하고 앞뒤 공백을 무시한다.

## 제2조 (기본 라우팅)

`subject_category` 에 따라 다음 큐로 보낸다.

| subject_category | 큐 |
|---|---|
| `billing` | `finance` |
| `technical` | `tech-support` |
| `account` | `account-ops` |
| 그 외 값 · 누락 | `general` |

## 제3조 (첨부파일)

`attachments`(리스트, 각 항목은 `size_bytes` 를 가진 dict)의 `size_bytes` 합이
**10,485,760 바이트를 초과**하면 제2조 대신 `large-files` 큐로 보낸다.
정확히 10,485,760 바이트는 초과가 아니다. `attachments` 누락·빈 리스트는 합 0 으로 본다.

## 제4조 (언어)

`language` 가 `ja` 또는 `zh` 면 제2·3조 대신 `intl` 큐로 보낸다.
지역 표기가 붙은 코드는 하이픈 앞부분으로 판정한다 (`zh-TW` → `zh`, `ja-JP` → `ja`).

## 제5조 (영업시간)

영업시간은 **평일(월~금) 09:00:00 이상 18:00:00 미만(KST)** 이다.
18:00:00 정각 접수는 영업시간 외다.

영업시간 외(주말 전체, 평일 09:00 이전, 평일 18:00:00 및 그 이후)에 접수된 티켓은
제2~4조 대신 `next-business-day` 큐로 보낸다.

`created_utc` 는 UTC 로 들어오므로 반드시 KST 로 변환한 뒤 요일·시각을 판정한다.

## 제6조 (VIP)

`vip` 가 참이면 제2~5조 대신 `vip` 큐로 보낸다.
VIP 는 24시간 대응하므로 **영업시간 규칙(제5조)을 적용하지 않는다**.

## 제7조 (VIP 청구 예외)

제6조에도 불구하고, VIP 티켓의 `subject_category` 가 `billing` 이면
`vip` 대신 `finance-priority` 큐로 보낸다. 이 경우에도 제5조는 적용하지 않는다.

## 제8조 (긴급)

`priority` 가 `urgent` 면 다른 모든 조항(제2~7조)에 우선해 `escalation` 큐로 보낸다.
언어·VIP·영업시간·첨부파일을 불문한다.

## 제9조 (priority 값)

유효한 값은 `urgent`, `high`, `normal`, `low` 다.
`urgent` 외의 값은 라우팅에 어떤 영향도 주지 않는다. 누락은 `normal` 로 본다.

## 제10조 (누락 필드)

- `vip` 누락 → 거짓으로 본다.
- `language` 누락 → 언어 규칙(제4조)을 적용하지 않는다.
- 알 수 없는 `subject_category` → 제2조의 "그 외" 로 `general` 취급.

## 제11조 (큐 이름)

반환값은 다음 중 하나의 소문자 문자열이어야 한다.

`finance` · `tech-support` · `account-ops` · `general` · `large-files` · `intl` ·
`next-business-day` · `vip` · `finance-priority` · `escalation`

## 제12조 (우선순위 요약)

여러 조항이 동시에 발동하면 다음 순서에서 앞에 있는 조항이 이긴다.

```
제8조(urgent) > 제7조(VIP×billing) > 제6조(VIP) > 제5조(영업시간)
             > 제4조(언어) > 제3조(첨부) > 제2조(기본)
```
