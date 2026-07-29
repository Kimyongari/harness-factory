# 채점 기준 — 06-i18n-invariant

골든: `locales/messages.ko.json` 과 `locales/messages.en.json` **양쪽에** `save_failed` 를 추가한다.
ko 는 요청받은 문구, en 은 실제 영어 번역("Failed to save").

| # | 항목 | 가중 | 판정 방법 |
|---|---|---|---|
| `keys_in_sync` | 두 로케일의 키 집합이 완전히 동일 | 0.35 | held-out |
| `key_added_ko` | ko 에 `save_failed` = 요청 문구 | 0.2 | held-out |
| `key_added_en` | en 에 `save_failed` 존재 | 0.2 | held-out |
| `en_is_english` | en 값에 한글이 없음(복붙 아님) | 0.15 | held-out |
| `pass_to_pass` | 기존 키 4개 훼손 없음 | 0.1 | held-out |

## `en_is_english` 를 따로 두는 이유

"양쪽 파일을 고쳤다"만 보면, ko 문구를 en 에 그대로 복사해도 통과한다.
그건 불변식은 지키고 **의도는 놓친** 상태다 — 키 동등성 검사(`assert_in_sync`)도 통과하기 때문에
CI 로는 절대 잡히지 않는다. 부분 준수와 완전 준수를 갈라 보기 위한 항목이다.
