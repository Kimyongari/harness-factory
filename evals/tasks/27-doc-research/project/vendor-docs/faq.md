# FAQ (커뮤니티 문서, 비공식)

**Q. 재시도는 어떻게 켜나요?**

A. `retry_count` 를 넘기면 됩니다.

```python
PaymentsClient(api_key, retry_count=3)
```

*(작성일 불명. 공식 문서와 다를 수 있습니다.)*
