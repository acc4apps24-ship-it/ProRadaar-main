from __future__ import annotations

import calendar
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any, Iterable

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
        summary = _normalize_summary(item.get("summary", item.get("description", "")))

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

    if parsed.get("bozo") and not entries:
        reason = parsed.get("bozo_exception", "unknown parser error")
        raise ValueError(f"Failed to parse feed: {reason}")

    return entries


def _published_at(item: Any) -> datetime | None:
    parsed_date = item.get("published_parsed") or item.get("updated_parsed")
    if parsed_date:
        return datetime.fromtimestamp(calendar.timegm(parsed_date[:9]), timezone.utc)

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


def _normalize_summary(value: Any) -> str:
    stripper = _HTMLTextExtractor()
    stripper.feed(str(value))
    stripper.close()
    text = unescape(stripper.text)
    return re.sub(r"\s+", " ", text).strip()


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    @property
    def text(self) -> str:
        return "".join(self._parts)

    def handle_data(self, data: str) -> None:
        self._parts.append(data)
