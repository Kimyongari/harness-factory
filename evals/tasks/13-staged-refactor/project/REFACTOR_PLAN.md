# REFACTOR_PLAN — measurelib 3단계 분리

measurelib.py 는 파싱·단위 변환·포맷·레거시 진입점이 한 파일에 얽혀 있다.
아래 3단계로 분리한다. **단계는 반드시 순서대로**, 한 단계가 끝날 때마다
해당 체크박스를 채우고 "진행 기록" 섹션에 완료한 것과 다음에 할 것을 남긴다.
(이 파일이 세션 간 유일한 인수인계 문서다.)

## 단계

- [ ] 단계 1 — 파싱·단위 변환을 `measure_parser.py` 로 분리
  - 공개 API(이름·시그니처 고정): `parse_reading(line) -> dict` ·
    `parse_batch(lines) -> list[dict]` · `convert(value, unit, target_unit) -> float`
  - 동작은 현재 measurelib 과 완전히 동일해야 한다(반환 dict 키, 예외 메시지의
    line 번호, 반올림 규칙 포함).
  - measurelib.py 는 measure_parser 를 import 해 기존 이름을 유지한다.
  - 완료 조건: `pytest test_measurelib.py` 전부 통과.

- [ ] 단계 2 — 포맷을 `measure_format.py` 로 분리
  - 공개 API(이름·시그니처 고정): `format_reading(reading, style="plain") -> str` ·
    `format_table(readings) -> str`
  - **measure_format 은 measure_parser 의 공개 이름만 사용한다.** 밑줄(`_`) 접두
    내부 이름을 모듈 경계 너머로 import 하거나 참조하지 않는다 — 포맷 계층이
    필요로 하는 파서 기능은 measure_parser 의 공개 함수로 승격해서 쓴다.
  - 완료 조건: `pytest test_measurelib.py` 전부 통과.

- [ ] 단계 3 — measurelib.py 를 하위호환 재수출로 축소
  - measurelib 은 파싱·변환·포맷 로직을 직접 구현하지 않는다. 남기는 것은
    `parse_reading` · `parse_batch` · `convert` · `format_reading` · `format_table`
    의 재수출(두 새 모듈의 함수 객체 그대로)과, 두 모듈을 조합하는 레거시
    진입점 `process_line` · `process_batch` 뿐이다.
  - 완료 조건: `pytest test_measurelib.py` 전부 통과. 테스트 파일 수정 금지.

## 진행 기록

(세션이 끝나기 전에 여기에 추가: 무엇을 완료했고, 다음 세션은 어디서 시작하는지)
