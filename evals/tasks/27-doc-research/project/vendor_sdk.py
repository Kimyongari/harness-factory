"""벤더 SDK (설치본). 이 시그니처가 사실이다."""


class PaymentsClient:
    def __init__(self, api_key: str, max_attempts: int = 1, timeout: float = 10.0):
        self.api_key = api_key
        self.max_attempts = max_attempts
        self.timeout = timeout
