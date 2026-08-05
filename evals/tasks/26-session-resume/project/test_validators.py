from validators import validate_email, validate_phone, validate_postal, validate_url


def test_valid_inputs():
    assert validate_email("a@b.com")
    assert validate_phone("010-1234-5678")
    assert validate_postal("06236")
    assert validate_url("https://example.com")
