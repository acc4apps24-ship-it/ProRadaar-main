from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from proradaar.models import FeedEntry, ScoredEntry


TRACKING_QUERY_PARAMS = {"fbclid", "gclid"}

TOPIC_KEYWORDS = {
    "onboarding": [
        "onboarding",
        "setup",
        "template",
        "getting started",
        "import",
        "migration",
        "workspace",
        "invite",
        "signup",
        "trial",
    ],
    "activation": [
        "activation",
        "adoption",
        "aha moment",
        "engagement",
        "workflow",
        "automation",
        "collaboration",
        "retention",
        "usage",
        "user journey",
    ],
    "monetisation": [
        "pricing",
        "billing",
        "plan",
        "upgrade",
        "expansion",
        "seats",
        "limits",
        "packaging",
        "enterprise",
        "freemium",
        "paywall",
    ],
    "product": [
        "product update",
        "changelog",
        "release",
        "feature",
        "launch",
        "integration",
        "marketplace",
        "ai feature",
        "growth",
    ],
}


def deduplicate_entries(entries: list[FeedEntry]) -> list[FeedEntry]:
    seen: set[str] = set()
    result: list[FeedEntry] = []
    for item in entries:
        key = _dedupe_key(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def filter_recent(entries: list[FeedEntry], hours: int) -> list[FeedEntry]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return [
        item
        for item in entries
        if item.published_at is None or _as_utc(item.published_at) >= cutoff
    ]


def score_entries(entries: list[FeedEntry], limit: int) -> list[ScoredEntry]:
    scored = [_score_entry(item) for item in entries]
    scored.sort(key=lambda item: (item.score, item.entry.source.priority), reverse=True)
    return scored[:limit]


def _score_entry(entry: FeedEntry) -> ScoredEntry:
    text = f"{entry.title} {entry.summary}".lower()
    matched_topics: list[str] = []
    score = entry.source.priority

    for topic, keywords in TOPIC_KEYWORDS.items():
        hits = sum(1 for keyword in keywords if _keyword_matches(text, keyword))
        if hits:
            matched_topics.append(topic)
            score += hits * 3

    return ScoredEntry(entry=entry, score=score, matched_topics=matched_topics)


def _dedupe_key(entry: FeedEntry) -> str:
    if entry.url:
        return _normalize_url(entry.url)
    normalized_title = re.sub(r"\W+", " ", entry.title.lower()).strip()
    return f"{entry.source.group}:{normalized_title}"


def _normalize_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    query_params = [
        (name, value)
        for name, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not _is_tracking_query_param(name)
    ]
    query = urlencode(sorted(query_params))

    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            query,
            "",
        )
    )


def _is_tracking_query_param(name: str) -> bool:
    normalized = name.lower()
    return normalized.startswith("utm_") or normalized in TRACKING_QUERY_PARAMS


def _keyword_matches(text: str, keyword: str) -> bool:
    escaped_words = [re.escape(word) for word in keyword.lower().split()]
    pattern = r"\s+".join(escaped_words)
    return re.search(rf"(?<!\w){pattern}(?!\w)", text) is not None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
