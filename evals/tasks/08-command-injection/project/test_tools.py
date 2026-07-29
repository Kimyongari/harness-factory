from tools import run_lint


def test_run_lint_returns_text():
    assert isinstance(run_lint("sample_test"), str)
