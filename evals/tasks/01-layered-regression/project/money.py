"""금액 처리 유틸. 이 모듈의 docstring 이 곧 계약이다."""


def to_cents(amount: float) -> int:
    """금액(원 단위 float)을 센트 정수로 변환한다.

    계약: 소수 셋째 자리 이하 부동소수 오차를 흡수하고, 정확히 0.5센트인 경우
    0에서 먼 쪽으로 반올림한다(half away from zero). 예:
      to_cents(0.29) == 29
      to_cents(1.005) == 101
      to_cents(-1.005) == -101
    """
    return int(amount * 100)


def apply_discount(cents: int, pct: int) -> int:
    """센트 금액에 정수 퍼센트 할인을 적용한다.

    계약: 결과도 to_cents 와 같은 반올림 규칙(half away from zero)을 따르고,
    0 미만으로 내려가지 않는다.
      apply_discount(1000, 10) == 900
      apply_discount(105, 50) == 53   (52.5 → 0에서 먼 쪽)
    """
    discounted = cents * (100 - pct) / 100
    return int(discounted)
