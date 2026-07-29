from api import get_user


def test_get_user_by_id():
    assert get_user(1)["name"] == "alice"
