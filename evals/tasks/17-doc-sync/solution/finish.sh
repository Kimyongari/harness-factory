#!/usr/bin/env bash
# 골든 마무리 — 골든 산출물 중 하나가 README.md 인데 solution/README.md 는 루브릭 자리다.
# (apply_golden 은 solution/README.md 를 채점 문서로 보고 복사하지 않는다) → 여기서 쓴다.
set -euo pipefail
cd "$1"
cat > README.md <<'DOC'
# userapi

사용자 조회 모듈.

## API

### `get_user(user_id=None, email=None)`

`user_id` 또는 `email` 로 사용자를 찾아 dict 를 돌려준다. 없으면 `None`.
둘 다 생략하면 `None` 을 돌려준다.

```python
from api import get_user

print(get_user(1))                          # id 로 조회
print(get_user(email="bob@example.com"))    # email 로 조회
```

## 테스트

`pytest -q`
DOC
