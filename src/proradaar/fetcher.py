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


USER_AGENT = "ProRadaar/0.1 RSS digest bot"


def fetch_all(
    sources: Iterable[Source],
    timeout_seconds: float = 15.0,
) -> tuple[list[FeedEntry], list[str]]:
    entries: list[FeedEntry] = []
    failures: list[str] = []

    with httpx.Client(
        timeout=timeout_seconds,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        for source in sources:
            try:
                response = client.get(source.url)
                response.raise_for_status()
                if source.source_type == "rss":
                    entries.extend(parse_feed(source, response.content))
                elif source.source_type == "markdown_release_notes":
                    entries.extend(
                        parse_markdown_release_notes(source, response.content)
                    )
                else:
                    raise ValueError(f"Unsupported source type: {source.source_type}")
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
        if _is_excluded(source, title, summary, url):
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


def parse_markdown_release_notes(source: Source, content: bytes) -> list[FeedEntry]:
    text = content.decode("utf-8", errors="replace")
    lines = text.splitlines()
    entries: list[FeedEntry] = []
    current_title: str | None = None
    current_summary: list[str] = []
    inside_latest_month = False

    for line in lines:
        if line.startswith("## "):
            if inside_latest_month:
                break
            inside_latest_month = True
            continue

        if not inside_latest_month:
            continue

        if line.startswith("### "):
            _append_markdown_entry(source, entries, current_title, current_summary)
            current_title = line.removeprefix("### ").strip()
            current_summary = []
            continue

        if current_title:
            stripped = line.strip()
            if stripped:
                current_summary.append(stripped)

    _append_markdown_entry(source, entries, current_title, current_summary)
    return entries


def _append_markdown_entry(
    source: Source,
    entries: list[FeedEntry],
    title: str | None,
    summary_parts: list[str],
) -> None:
    if not title:
        return

    summary = _normalize_markdown_summary(" ".join(summary_parts))
    url = f"{source.url}#{_markdown_anchor(title)}"
    if _is_excluded(source, title, summary, url):
        return

    entries.append(
        FeedEntry(
            source=source,
            title=title,
            url=url,
            published_at=None,
            summary=summary,
        )
    )


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


def _normalize_markdown_summary(value: str) -> str:
    without_links = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    without_markup = without_links.replace("`", "").replace("*", "")
    return re.sub(r"\s+", " ", without_markup).strip()


def _is_excluded(source: Source, *values: str) -> bool:
    text = " ".join(values).lower()
    return any(
        keyword.lower() in text
        for keyword in source.exclude_keywords
        if keyword.strip()
    )


def _markdown_anchor(title: str) -> str:
    normalized = re.sub(r"[^\w\s-]", "", title.lower())
    normalized = re.sub(r"[\s_]+", "-", normalized).strip("-")
    return normalized


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    @property
    def text(self) -> str:
        return "".join(self._parts)

    def handle_data(self, data: str) -> None:
        self._parts.append(data)
