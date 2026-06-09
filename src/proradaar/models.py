from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    group: str
    priority: int = 0
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FeedEntry:
    source: Source
    title: str
    url: str
    published_at: datetime | None
    summary: str


@dataclass(frozen=True)
class ScoredEntry:
    entry: FeedEntry
    score: int
    matched_topics: list[str]
