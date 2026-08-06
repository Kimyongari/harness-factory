# 02 · API 마이그레이션 (swe-maintenance · hard)

**질의**: `config.legacy.get(section, key, default="")` 호출 14곳(4개 파일)을
`config.store.lookup(path, *, default=None)` 으로 이전하고 legacy.py 를 삭제하라.
모든 호출부의 동작은 불변이어야 한다.

**함정 구조** (설계 원칙 ② 계층 숨은 결함 + ① 계약 엄격함): 두 API 의 계약 차이는
docstring 에 명시돼 있다 — 구 API 는 (a) 항상 str 반환(bool 은 "true"/"false"),
(b) 키 부재 시 default("") 반환. 신 API 는 (a) 타입 보존(int 는 int), (b) 키 부재 시
None. 14곳 중 12곳은 기계적 치환으로도 동작이 같지만, 2곳이 구 API quirk 에 의존한다:

1. **존재-truthiness quirk** — `http_client.retry_limit()` 은 `if raw:` 로
   "설정에 값이 있는가"를 판별한다. 구 API 에서는 존재하는 값이 항상 비어 있지 않은
   str 이라 이 판별이 옳았다. settings.json 에는 `retries: 0` 이 명시돼 있다 —
   기계적으로 lookup 으로 바꾸면 0 이 falsy 라 **조용히** 기본 3 으로 바뀐다.
2. **str 전제 quirk** — `server.base_url()` 이 `get("server","port")` 반환값을
   문자열 연결로 조립한다. lookup 은 8080(int) 을 돌려주므로 기계적 치환은
   TypeError — 보이는 테스트가 이 함수를 부르지 않아 치환 직후에는 드러나지 않는다.

**보이는 테스트는 quirk 경로를 건드리지 않는다**: test_app.py 는 retry_limit ·
base_url · log_format(키 부재 경로)을 부르지 않는다. 기계적 치환 + 보이는 테스트
확인만으로 멈춘 실행은 gate(0.25)만 얻고 falsy(0.3)·typed(0.3)에서 떨어진다.

**채점**: gate = legacy.py 삭제 + legacy import 잔존 없음(정규식) + held-out 의
보이는-동작 미러 통과. 숨은 계층 = falsy 경로(0 유지)·타입 경로(base_url 조립)·
회귀(키 부재 기본값, 반환 타입). 에이전트가 test_app.py 를 고쳐도 held-out 사본이
원 사양을 판정한다.

**왜 이 태스크인가**: "치환 + 보이는 테스트 통과" 에서 멈추는 실행과, 프롬프트가
요구한 "동작 불변"을 호출부마다 두 계약을 대조해 검증한 실행이 갈린다. verify
게이트가 검증 루프를 강제하는지를 잰다.

**함정이 아닌 것**: 오도하는 주석 없음. 두 API 의 계약 차이는 각 모듈 docstring 에
예시 수준까지 명시돼 있고, quirk 데이터(`retries: 0`, port int)는 settings.json 에
그대로 보인다. 어려움은 기만이 아니라 의미 차이의 전수 대조에서 나온다.
