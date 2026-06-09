from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable, Any

import feedparser
import httpx

from proradaar.models import FeedEntry, Source


def fetch_all(
    sources: Iterable[Source],
    timeout_seconds: float = 15.0,
) -> tuple[list[FeedEntry], list[str]]:
    entries: list[FeedEntry] = []
    failures: list[str] = []

    with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
        for source in sources:
            try:
                response = client.get(source.url)
                response.raise_for_status()
                entries.extend(parse_feed(source, response.content))
            except Exception as exc:
                failures.append(f"{source.name}: {exc}")

    return entries, failures


def parse_feed(source: Source, content: bytes) -> list[FeedEntry]:
    parsed = feedparser.parse(content)
    entries: list[FeedEntry] = []

    for item in parsed.entries:
        title = item.get("title", "").strip()
        url = item.get("link", "").strip()
        summary = item.get("summary", item.get("description", "")).strip()

        if not title or not url:
            continue

        entries.append(
            FeedEntry(
                source,
                title,
                url,
                _published_at(item),
                summary,
            )
        )

    return entries


def _published_at(item: Any) -> datetime | None:
    date_value = item.get("published") or item.get("updated")
    if not date_value:
        return None

    try:
        parsed = parsedate_to_datetime(date_value)
    except (TypeError, ValueError):
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)
