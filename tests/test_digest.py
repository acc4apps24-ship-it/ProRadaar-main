from datetime import datetime, timezone

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
