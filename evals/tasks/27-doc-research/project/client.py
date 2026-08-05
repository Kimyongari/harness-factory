from vendor_sdk import PaymentsClient


def make_client(api_key: str) -> PaymentsClient:
    # 재시도 설정이 빠져 있다 — 실패 시 한 번만 시도한다.
    return PaymentsClient(api_key)
