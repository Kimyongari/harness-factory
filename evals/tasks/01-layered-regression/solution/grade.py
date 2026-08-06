import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from grading import Report, run_heldout, workspace  # noqa: E402

HELDOUT = Path(__file__).parent / "heldout"
ws = workspace()
r = Report()

# 계층 ①: 보이는 버그. 이걸 못 고치면 요청한 작업 자체를 안 한 것이다.
ok, log = run_heldout(ws, HELDOUT, expr="gate")
r.add("fail_to_pass", "대량 할인 임계값 수정(보이는 버그)", 0.25, ok, log if not ok else "", gate=True)

# 계층 ②: money 계약 — 보이는 테스트가 덮지 않는 반올림·부동소수 경계.
ok, log = run_heldout(ws, HELDOUT, expr="money")
r.add("money_contract", "money 계약(half away from zero·오차 흡수)", 0.35, ok, log if not ok else "")

# 계층 ③: refunds 계약 — money 를 고쳐야만 드러나는 의존 결함.
ok, log = run_heldout(ws, HELDOUT, expr="refund")
r.add("refund_contract", "환불이 청구의 정확한 역", 0.25, ok, log if not ok else "")

# 회귀 없음.
ok, log = run_heldout(ws, HELDOUT, expr="regression")
r.add("no_regression", "기존 동작 회귀 없음", 0.15, ok, log if not ok else "")

r.emit()
