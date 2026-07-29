# 기여 규칙

## 로케일 (중요)

`locales/messages.<lang>.json` 은 **모든 로케일의 키 집합이 항상 동일해야 한다.**
한쪽에만 키를 추가하면 다른 언어 사용자에게 `KeyError` 가 발생한다.

- 메시지를 추가·삭제할 때는 `locales/` 의 **모든 파일을 함께** 수정한다.
- 수정 후 `python -c "import loader; loader.assert_in_sync()"` 로 확인한다.
- 번역이 확정되지 않았더라도 키는 반드시 넣는다(값은 원문 그대로라도).

## 테스트

`pytest -q`
