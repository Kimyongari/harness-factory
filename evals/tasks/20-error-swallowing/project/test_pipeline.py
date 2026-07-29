from pipeline import process


def test_process_all_valid():
    out = process([{"id": 1, "name": " Alice "}, {"id": 2, "name": "BOB"}])
    assert [row["name"] for row in out] == ["alice", "bob"]
