from datetime import datetime, timezone

from proradaar.models import FeedEntry, ScoredEntry, Source
from proradaar.summarizer import build_prompt


def test_build_prompt_includes_context_items_and_failures():
    source = Source(
        name="Lenny",
        url="https://example.com/feed",
        group="influencers",
    )
    scored = [
        ScoredEntry(
            entry=FeedEntry(
                source=source,
                title="Activation lessons",
                url="https://example.com/post",
                summary="Trial users reach activation faster with guided setup.",
                published_at=datetime.now(timezone.utc),
            ),
            score=12,
            matched_topics=["activation", "onboarding"],
        ),
    ]

    prompt = build_prompt(scored, failures=["Broken Feed: timeout"])

    assert "senior product manager" in prompt
    assert "на русском" in prompt
    assert "Activation lessons" in prompt
    assert "https://example.com/post" in prompt
    assert "Broken Feed: timeout" in prompt
    assert "onboarding" in prompt
    assert "activation" in prompt
    assert "monetisation" in prompt
