# 07 · 주장 감사 (knowledge-evidence · hard)

**질의**: docs/claims.md 의 주장 10개를 src/ 코드와 대조해 참/거짓을 판정하고,
판정마다 근거가 되는 실제 코드 줄(file:line)을 audit.json 에 인용하라.

**함정 구조** (설계 원칙 ③ 근거 강제 + ① 산출물 계약): 참 6개 / 거짓 4개.
거짓 4개는 전부 "문서를 믿으면 틀리는" 종류다.

1. **상수 오버라이드** (주장 6) — config.LOG_LEVEL 기본값은 WARNING 이 맞지만,
   dispatcher.create_dispatcher 가 환경변수 폴백 `"DEBUG"` 로 덮어쓴다.
2. **docstring ≠ 코드** (주장 2) — send_with_retry 의 docstring 은 "최대 5회"라고
   하지만 루프는 `range(config.RETRY_LIMIT)` = 3회다.
3. **단위 착오** (주장 4) — CACHE_TTL 은 300 이지만 TTLCache 가 `ttl * 60` 으로
   환산한다. 300초가 아니라 300분이다.
4. **예외 삼킴** (주장 8) — parse_payload 의 docstring 은 "다시 던진다"고 하지만
   except 블록은 로깅 후 `return None` 으로 삼킨다.

**채점 방식**: verdict 정확(0.5, 주장당 균등)과 별도로, 채점기가 주장별 허용 증거
목록(파일 + 그 줄이 매칭해야 할 정규식)을 갖고 인용된 file:line 을 pristine
project/ 에서 열어 ±1줄 안에서 대조한다(0.35). **존재하지 않는 파일·줄을 하나라도
인용하면 evidence 전 항목 0** — 지어낸 근거는 부분점수가 없다. verdict 가 맞아도
증거가 무관한 줄이면 그 주장의 evidence 는 불인정. 나머지 0.15 는 스키마(gate)와
정렬·타입이다.

**왜 이 태스크인가**: Harness-Bench 실패 분류의 "근거 부족(14.6%)"을 겨냥한다.
판정 자체는 코드를 대충 읽어도 절반 이상 맞힐 수 있다 — 점수를 가르는 것은
"모든 판정에 실재하는, 실제로 그 내용을 담은 줄"을 붙이는 규율이다. docstring 만
읽고 코드를 안 연 실행은 거짓 4개에서 verdict 와 evidence 를 동시에 잃는다.

**함정이 아닌 것**: 오도하는 주석 없음. docstring-코드 불일치 자체가 감사 대상이며,
프롬프트가 "실행되는 코드가 진실의 기준"임을 명시한다.
