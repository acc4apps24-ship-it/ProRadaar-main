import json

import httpx
import pytest

from proradaar.telegram import send_telegram_message, split_telegram_message


def test_split_telegram_message_keeps_short_message_intact():
    assert split_telegram_message("hello", limit=10) == ["hello"]


def test_split_telegram_message_splits_on_line_boundaries():
    message = "line one\nline two\nline three"

    assert split_telegram_message(message, limit=15) == [
        "line one\n",
        "line two\n",
        "line three",
    ]


def test_split_telegram_message_splits_long_line():
    assert split_telegram_message("abcdefghij", limit=4) == ["abcd", "efgh", "ij"]


def test_split_telegram_message_treats_empty_message_as_no_chunks():
    assert split_telegram_message("") == []


def test_split_telegram_message_keeps_exact_limit_message_intact():
    assert split_telegram_message("abcd", limit=4) == ["abcd"]


def test_split_telegram_message_preserves_trailing_newline():
    chunks = split_telegram_message("hello\n", limit=10)

    assert chunks == ["hello\n"]
    assert "".join(chunks) == "hello\n"


def test_split_telegram_message_preserves_leading_blank_before_long_line():
    message = "\nabcdefghij"
    chunks = split_telegram_message(message, limit=4)

    assert chunks == ["\n", "abcd", "efgh", "ij"]
    assert "".join(chunks) == message


def test_split_telegram_message_preserves_content_and_limit_invariants():
    message = "line one\nabcdefghijklmnopqrstuvwxyz\n\nlast"
    chunks = split_telegram_message(message, limit=8)

    assert chunks
    assert all(chunks)
    assert all(len(chunk) <= 8 for chunk in chunks)
    assert "".join(chunks) == message


def test_send_telegram_message_posts_each_chunk_in_order(monkeypatch):
    requests = []
    real_client = httpx.Client

    def handler(request):
        requests.append((str(request.url), json.loads(request.content)))
        return httpx.Response(200, request=request)

    def client_factory(*, timeout):
        assert timeout == 15.0
        return real_client(transport=httpx.MockTransport(handler), timeout=timeout)

    monkeypatch.setattr("proradaar.telegram.httpx.Client", client_factory)

    send_telegram_message("token", "chat", "a" * 3901)

    assert requests == [
        (
            "https://api.telegram.org/bottoken/sendMessage",
            {
                "chat_id": "chat",
                "text": "a" * 3900,
                "disable_web_page_preview": True,
            },
        ),
        (
            "https://api.telegram.org/bottoken/sendMessage",
            {
                "chat_id": "chat",
                "text": "a",
                "disable_web_page_preview": True,
            },
        ),
    ]


def test_send_telegram_message_raises_for_failed_response(monkeypatch):
    real_client = httpx.Client

    def handler(request):
        return httpx.Response(500, request=request)

    def client_factory(*, timeout):
        return real_client(transport=httpx.MockTransport(handler), timeout=timeout)

    monkeypatch.setattr("proradaar.telegram.httpx.Client", client_factory)

    with pytest.raises(httpx.HTTPStatusError):
        send_telegram_message("token", "chat", "hello")


def test_send_telegram_message_does_not_post_empty_message(monkeypatch):
    requests = []
    real_client = httpx.Client

    def handler(request):
        requests.append(request)
        return httpx.Response(200, request=request)

    def client_factory(*, timeout):
        return real_client(transport=httpx.MockTransport(handler), timeout=timeout)

    monkeypatch.setattr("proradaar.telegram.httpx.Client", client_factory)

    send_telegram_message("token", "chat", "")

    assert requests == []
