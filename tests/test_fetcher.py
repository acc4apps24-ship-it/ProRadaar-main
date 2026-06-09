from proradaar.fetcher import parse_feed
from proradaar.models import Source


def test_parse_feed_extracts_entries():
    source = Source(
        name="Example",
        url="https://example.com/feed",
        group="industry_us",
    )
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

    entries = parse_feed(source, content)

    assert len(entries) == 1
    assert entries[0].title == "New onboarding flow"
    assert entries[0].url == "https://example.com/onboarding"
    assert entries[0].summary == "Setup improvements for new teams."
    assert entries[0].published_at is not None
