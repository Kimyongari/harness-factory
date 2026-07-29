from weather import BASE_URL


def test_base_url():
    assert BASE_URL.startswith("https://")
