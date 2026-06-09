from proradaar.telegram import split_telegram_message


def test_split_telegram_message_keeps_short_message_intact():
    assert split_telegram_message("hello", limit=10) == ["hello"]


def test_split_telegram_message_splits_on_line_boundaries():
    message = "line one\nline two\nline three"

    assert split_telegram_message(message, limit=15) == [
        "line one",
        "line two",
        "line three",
    ]


def test_split_telegram_message_splits_long_line():
    assert split_telegram_message("abcdefghij", limit=4) == ["abcd", "efgh", "ij"]
