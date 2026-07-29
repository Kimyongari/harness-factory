from pricebook import PriceBook


def test_lookup():
    book = PriceBook({"A": 100, "B": 200})
    assert book.lookup("A") == 100
    assert book.lookup("Z") is None
