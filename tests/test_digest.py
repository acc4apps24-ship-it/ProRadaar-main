from datetime import datetime, timezone

import pytest

import proradaar.digest as digest
from proradaar.digest import build_digest
from proradaar.models import FeedEntry, Source


def test_build_digest_returns_prompt_with_scored_recent_items():
    source = Source(
        name="Example",
        url="https://example.com/feed",
        group="industry_us",
        priority=5,
    )
    entries = [
        FeedEntry(
            source=source,
            title="New trial onboarding",
            url="https://example.com/onboarding",
            published_at=datetime.now(timezone.utc),
            summary="A launch about setup and activation.",
        ),
    ]

    prompt = build_digest(entries, failures=[], max_items=10, recent_hours=36)

    assert "New trial onboarding" in prompt
    assert "senior product manager" in prompt


def test_main_dry_run_prints_prompt_without_llm_or_telegram_env(monkeypatch, capsys):
    source = _source()
    entry = _entry(source)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setattr(digest, "load_sources", lambda path: [source])
    monkeypatch.setattr(digest, "fetch_all", lambda sources: ([entry], []))
    monkeypatch.setattr(
        digest,
        "summarize_with_llm",
        lambda prompt, model: pytest.fail("dry-run must not call LLM"),
    )
    monkeypatch.setattr(
        digest,
        "send_telegram_message",
        lambda token, chat_id, message: pytest.fail(
            "dry-run must not send Telegram"
        ),
    )

    digest.main(["--dry-run", "--max-items", "10"])

    output = capsys.readouterr().out
    assert "New trial onboarding" in output
    assert "senior product manager" in output


def test_main_reads_telegram_env_before_summarizing(monkeypatch):
    source = _source()
    entry = _entry(source)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setattr(digest, "load_sources", lambda path: [source])
    monkeypatch.setattr(digest, "fetch_all", lambda sources: ([entry], []))
    monkeypatch.setattr(
        digest,
        "summarize_with_llm",
        lambda prompt, model: pytest.fail(
            "missing Telegram env must fail before LLM call"
        ),
    )

    with pytest.raises(KeyError):
        digest.main([])


def test_main_all_source_failure_sends_deterministic_note_without_llm(monkeypatch):
    sent = []
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setattr(digest, "load_sources", lambda path: [_source()])
    monkeypatch.setattr(
        digest,
        "fetch_all",
        lambda sources: ([], ["Example: timeout", "Other: bad feed"]),
    )
    monkeypatch.setattr(
        digest,
        "summarize_with_llm",
        lambda prompt, model: pytest.fail(
            "all-source failure must not call LLM"
        ),
    )
    monkeypatch.setattr(
        digest,
        "send_telegram_message",
        lambda token, chat_id, message: sent.append((token, chat_id, message)),
    )

    digest.main([])

    assert sent == [
        (
            "token",
            "chat",
            "Digest could not be generated: no feed entries were fetched. "
            "Source failures: Example: timeout; Other: bad feed",
        )
    ]


def test_main_llm_failure_sends_failure_note_and_reraises(monkeypatch):
    source = _source()
    entry = _entry(source)
    sent = []
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setattr(digest, "load_sources", lambda path: [source])
    monkeypatch.setattr(digest, "fetch_all", lambda sources: ([entry], []))

    def fail_llm(prompt: str, model: str) -> str:
        raise RuntimeError("OpenAI unavailable")

    monkeypatch.setattr(digest, "summarize_with_llm", fail_llm)
    monkeypatch.setattr(
        digest,
        "send_telegram_message",
        lambda token, chat_id, message: sent.append((token, chat_id, message)),
    )

    with pytest.raises(RuntimeError, match="OpenAI unavailable"):
        digest.main(["--max-items", "10"])

    assert sent == [
        (
            "token",
            "chat",
            "Digest generation failed during LLM summarization. "
            "Candidate count: 1. Error: OpenAI unavailable",
        )
    ]


def test_main_successful_non_dry_run_summarizes_and_sends_digest(monkeypatch):
    source = _source()
    entry = _entry(source)
    llm_calls = []
    sent = []
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setattr(digest, "load_sources", lambda path: [source])
    monkeypatch.setattr(digest, "fetch_all", lambda sources: ([entry], []))

    def summarize(prompt: str, model: str) -> str:
        llm_calls.append((prompt, model))
        return "Digest content"

    monkeypatch.setattr(digest, "summarize_with_llm", summarize)
    monkeypatch.setattr(
        digest,
        "send_telegram_message",
        lambda token, chat_id, message: sent.append((token, chat_id, message)),
    )

    digest.main(["--model", "test-model"])

    assert len(llm_calls) == 1
    assert "New trial onboarding" in llm_calls[0][0]
    assert llm_calls[0][1] == "test-model"
    assert sent == [("token", "chat", "Digest content")]


def _source() -> Source:
    return Source(
        name="Example",
        url="https://example.com/feed",
        group="industry_us",
        priority=5,
    )


def _entry(source: Source) -> FeedEntry:
    return FeedEntry(
        source=source,
        title="New trial onboarding",
        url="https://example.com/onboarding",
        published_at=datetime.now(timezone.utc),
        summary="A launch about setup and activation.",
    )
