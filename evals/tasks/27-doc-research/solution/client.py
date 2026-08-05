from vendor_sdk import PaymentsClient


def make_client(api_key: str) -> PaymentsClient:
    # migration.md 기준: v2 는 max_attempts(총 시도 횟수)를 쓴다.
    return PaymentsClient(api_key, max_attempts=3)
