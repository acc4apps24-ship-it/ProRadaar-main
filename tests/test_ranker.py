from datetime import datetime, timedelta, timezone

from proradaar.models import FeedEntry, Source
from proradaar.ranker import deduplicate_entries, filter_recent, score_entries


SOURCE = Source(name="Test", url="https://example.com/feed", group="company_changelogs")


def entry(title: str, url: str, summary: str, hours_old: int = 1) -> FeedEntry:
    return FeedEntry(
        source=SOURCE,
        title=title,
        url=url,
        summary=summary,
        published_at=datetime.now(timezone.utc) - timedelta(hours=hours_old),
    )


def test_deduplicate_entries_prefers_first_url():
    entries = [
        entry("New onboarding templates", "https://example.com/a", "First"),
        entry("New onboarding templates", "https://example.com/a", "Duplicate"),
    ]

    result = deduplicate_entries(entries)

    assert len(result) == 1
    assert result[0].summary == "First"


def test_deduplicate_entries_normalizes_tracking_urls():
    entries = [
        entry(
            "Product update",
            "https://example.com/post?utm_source=rss#comments",
            "First",
        ),
        entry("Product update", "https://example.com/post", "Duplicate"),
    ]

    result = deduplicate_entries(entries)

    assert len(result) == 1
    assert result[0].summary == "First"


def test_filter_recent_keeps_items_inside_window():
    entries = [
        entry("Recent activation update", "https://example.com/recent", "Recent", hours_old=2),
        entry("Old pricing update", "https://example.com/old", "Old", hours_old=72),
    ]

    result = filter_recent(entries, hours=36)

    assert [item.url for item in result] == ["https://example.com/recent"]


def test_score_entries_prioritizes_pm_keywords_and_source_priority():
    high_priority_source = Source(
        name="Important",
        url="https://example.com/feed",
        group="influencers",
        priority=10,
    )
    entries = [
        FeedEntry(
            source=high_priority_source,
            title="Activation playbook for trial onboarding",
            url="https://example.com/activation",
            summary="A new workflow helps users reach the aha moment faster.",
            published_at=datetime.now(timezone.utc),
        ),
        entry("Office photos", "https://example.com/photos", "Team event photos"),
    ]

    result = score_entries(entries, limit=10)

    assert result[0].entry.url == "https://example.com/activation"
    assert result[0].score > result[1].score
    assert "activation" in result[0].matched_topics
    assert "onboarding" in result[0].matched_topics


def test_score_entries_does_not_match_keywords_inside_unrelated_words():
    entries = [
        entry(
            "Important planning planet",
            "https://example.com/planning",
            "Important planning planet",
        ),
    ]

    result = score_entries(entries, limit=10)

    assert result[0].score == 0
    assert result[0].matched_topics == []
