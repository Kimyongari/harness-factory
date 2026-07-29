import config


def test_defaults():
    assert config.RETRIES == 3
    assert config.BASE_URL.startswith("https://")
