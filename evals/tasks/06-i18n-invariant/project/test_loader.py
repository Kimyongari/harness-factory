from loader import load, t


def test_load_ko():
    assert load("ko")["save_ok"] == "저장했습니다"


def test_translate():
    assert t("app_title", "en") == "Notepad"
