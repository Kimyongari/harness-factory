from users import find_user


def test_find_user():
    assert find_user("alice")[0][1] == "alice"
