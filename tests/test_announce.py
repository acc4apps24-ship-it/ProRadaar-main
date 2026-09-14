import pytest

import proradaar.announce as announce


def test_main_sends_announcement_then_default_poll(monkeypatch):
    sent_messages = []
    sent_polls = []
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setattr(
        announce,
        "send_telegram_message",
        lambda token, chat_id, message: sent_messages.append(
            (token, chat_id, message)
        ),
    )
    monkeypatch.setattr(
        announce,
        "send_telegram_poll",
        lambda token, chat_id, question, options: sent_polls.append(
            (token, chat_id, question, options)
        ),
    )

    announce.main(["--message", "ProRadaar updated"])

    assert sent_messages == [("token", "chat", "ProRadaar updated")]
    assert sent_polls == [
        (
            "token",
            "chat",
            "Как вам обновление ProRadaar?",
            ["Супер", "Не одобряю"],
        )
    ]


def test_main_requires_message(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")

    with pytest.raises(SystemExit):
        announce.main([])
