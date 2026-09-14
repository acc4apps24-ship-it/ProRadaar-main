import pytest

import proradaar.fetcher as fetcher
from proradaar.fetcher import fetch_all, parse_feed, parse_markdown_release_notes
from proradaar.models import Source


SOURCE = Source(
    name="Example",
    url="https://example.com/feed",
    group="industry_us",
)


def test_fetch_all_sends_user_agent(monkeypatch):
    client_kwargs = {}

    class FakeResponse:
        content = b"""
<rss version="2.0">
  <channel>
    <item>
      <title>Product update</title>
      <link>https://example.com/post</link>
    </item>
  </channel>
</rss>
"""

        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, **kwargs):
            client_kwargs.update(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def get(self, url):
            return FakeResponse()

    monkeypatch.setattr(fetcher.httpx, "Client", FakeClient)

    entries, failures = fetch_all([SOURCE])

    assert len(entries) == 1
    assert failures == []
    assert client_kwargs["headers"]["User-Agent"].startswith("ProRadaar/")


def test_parse_feed_extracts_entries():
    content = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example Feed</title>
    <item>
      <title>New onboarding flow</title>
      <link>https://example.com/onboarding</link>
      <description>Setup improvements for new teams.</description>
      <pubDate>Tue, 09 Jun 2026 08:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

    entries = parse_feed(SOURCE, content)

    assert len(entries) == 1
    assert entries[0].title == "New onboarding flow"
    assert entries[0].url == "https://example.com/onboarding"
    assert entries[0].summary == "Setup improvements for new teams."
    assert entries[0].published_at is not None


def test_parse_feed_excludes_entries_matching_source_keywords():
    source = Source(
        name="Lenny's Newsletter",
        url="https://example.com/feed",
        group="influencers",
        exclude_keywords=["community wisdom"],
    )
    content = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example Feed</title>
    <item>
      <title>Community Wisdom: onboarding teardown</title>
      <link>https://example.com/community-wisdom</link>
      <description>Paid member discussion.</description>
    </item>
    <item>
      <title>New onboarding flow</title>
      <link>https://example.com/onboarding</link>
      <description>Setup improvements for new teams.</description>
    </item>
  </channel>
</rss>
"""

    entries = parse_feed(source, content)

    assert [entry.title for entry in entries] == ["New onboarding flow"]


def test_parse_markdown_release_notes_reads_current_month_sections():
    source = Source(
        name="xAI Grok Release Notes",
        url="https://docs.x.ai/developers/release-notes.md",
        group="company_changelogs",
    )
    content = b"""# Release Notes

## September

### Grok Bot

Grok Bot is now available.

### Grok 4.6

Grok 4.6 is now available on the xAI API.

## August

### Imagine image API updates

Older content.
"""

    entries = parse_markdown_release_notes(source, content)

    assert [entry.title for entry in entries] == ["Grok Bot", "Grok 4.6"]
    assert entries[0].url == "https://docs.x.ai/developers/release-notes.md#grok-bot"
    assert entries[0].summary == "Grok Bot is now available."
    assert entries[0].published_at is None


def test_parse_feed_reads_atom_updated_dates():
    content = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Example Feed</title>
  <entry>
    <title>New activation guide</title>
    <link href="https://example.com/activation" />
    <updated>2026-06-09T08:00:00Z</updated>
    <summary>Activation improvements.</summary>
  </entry>
</feed>
"""

    entries = parse_feed(SOURCE, content)

    assert len(entries) == 1
    assert entries[0].published_at is not None


def test_parse_feed_normalizes_html_summaries():
    content = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example Feed</title>
    <item>
      <title>HTML summary</title>
      <link>https://example.com/html</link>
      <description><![CDATA[<p>Hello&nbsp;there</p>]]></description>
      <pubDate>Tue, 09 Jun 2026 08:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

    entries = parse_feed(SOURCE, content)

    assert entries[0].summary == "Hello there"


def test_parse_feed_raises_for_bad_feed_without_usable_entries():
    with pytest.raises(ValueError, match="Failed to parse feed"):
        parse_feed(SOURCE, b"not a feed")
