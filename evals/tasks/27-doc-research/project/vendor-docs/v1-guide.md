# Payments SDK v1 Guide

> **DEPRECATED** — 이 문서는 SDK v1 기준입니다. v2 이상에서는 `migration.md` 를 보세요.

## 재시도

```python
PaymentsClient(api_key, retries=3)
```

`retries` 는 실패 시 재시도 횟수입니다.
