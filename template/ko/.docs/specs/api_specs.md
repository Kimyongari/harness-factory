# API 명세 / 참고 지식 베이스

> 에이전트가 **필요할 때 읽는 수동적 지식**을 모아두는 곳입니다.
> API 명세, 레거시 시스템 구조, 도메인 용어집 등을 자유롭게 추가하세요.
> 능동적인 "수행 절차"는 `.skills/`에 두세요.

## 예시: 내부 API

### `GET /v1/users/{id}`
- 설명: 사용자 단건 조회
- 응답: `{ "id": str, "name": str, "created_at": iso8601 }`

## 도메인 용어
- **하네스(Harness)**: LLM을 에이전트로 작동시키는 주변 시스템 일체
- **IR**: 프레임워크 중립 중간 표현(Intermediate Representation)
