import pytest

from proradaar.fetcher import parse_feed
from proradaar.models import Source


SOURCE = Source(
    name="Example",
    url="https://example.com/feed",
    group="industry_us",
)


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
