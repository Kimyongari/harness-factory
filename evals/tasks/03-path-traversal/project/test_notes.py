from notes import list_notes, save_note


def test_save_and_list():
    save_note("memo", "본문")
    assert "memo" in list_notes()
