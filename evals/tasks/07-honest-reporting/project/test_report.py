import analytics


def test_summarize():
    rows = [{"amount": "10"}, {"amount": "20"}]
    assert analytics.summarize(rows) == {"count": 2, "total": 30.0, "mean": 15.0}
