# userapi

사용자 조회 모듈.

## API

### `get_user(user_id)`

id 로 사용자를 찾아 dict 를 돌려준다. 없으면 `None`.

```python
from api import get_user

print(get_user(1))
```

## 테스트

`pytest -q`
