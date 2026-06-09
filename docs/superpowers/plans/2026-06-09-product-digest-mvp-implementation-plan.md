# Product Digest MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify a low-cost daily Telegram digest for product management and SaaS updates, focused on onboarding, activation, and monetisation.

**Architecture:** A small Python package fetches RSS/Atom feeds from `sources.yaml`, normalizes and deduplicates entries, scores PM relevance locally, sends a capped candidate list to an OpenAI-compatible LLM, and delivers the final Russian digest to Telegram. GitHub Actions runs the package daily and supports manual runs.

**Tech Stack:** Python 3.12, `feedparser`, `PyYAML`, `httpx`, `openai`, `pytest`, GitHub Actions, Telegram Bot API.

---

## File Structure

- Create `pyproject.toml`: package metadata, dependencies, pytest config, console script.
- Create `sources.yaml`: initial RSS/Atom/Substack source list grouped by influencer, company, and market sources.
- Create `src/proradaar/__init__.py`: package marker.
- Create `src/proradaar/config.py`: load and validate source config and environment settings.
- Create `src/proradaar/models.py`: typed dataclasses for sources, feed entries, scored items, and run results.
- Create `src/proradaar/fetcher.py`: fetch and parse RSS/Atom feeds.
- Create `src/proradaar/ranker.py`: deduplicate, filter recent entries, and score PM relevance.
- Create `src/proradaar/summarizer.py`: build LLM prompt and call OpenAI-compatible chat completions.
- Create `src/proradaar/telegram.py`: split and send Telegram messages.
- Create `src/proradaar/digest.py`: CLI orchestration and dry-run mode.
- Create `.github/workflows/daily-digest.yml`: scheduled and manual GitHub Actions workflow.
- Create tests under `tests/` for config loading, ranking, Telegram splitting, and dry-run orchestration.

---

### Task 1: Python Package Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/proradaar/__init__.py`

- [ ] **Step 1: Create package config**

Create `pyproject.toml`:

```toml
[project]
name = "proradaar"
version = "0.1.0"
description = "Daily PM and SaaS digest focused on onboarding, activation, and monetisation."
requires-python = ">=3.12"
dependencies = [
  "feedparser>=6.0.11",
  "httpx>=0.27.0",
  "openai>=1.40.0",
  "python-dateutil>=2.9.0",
  "PyYAML>=6.0.1",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2.0",
]

[project.scripts]
proradaar-digest = "proradaar.digest:main"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: Create package marker**

Create `src/proradaar/__init__.py`:

```python
"""ProRadaar daily PM and SaaS digest."""
```

- [ ] **Step 3: Install dependencies**

Run:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

Expected: package installs without resolver errors.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml src/proradaar/__init__.py
git commit -m "chore: add python package skeleton"
```

---

### Task 2: Source Config Loading

**Files:**
- Create: `sources.yaml`
- Create: `src/proradaar/models.py`
- Create: `src/proradaar/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write config tests**

Create `tests/test_config.py`:

```python
from pathlib import Path

from proradaar.config import load_sources


def test_load_sources_reads_grouped_yaml(tmp_path: Path):
    config_path = tmp_path / "sources.yaml"
    config_path.write_text(
        """
sources:
  - name: Lenny's Newsletter
    url: https://www.lennysnewsletter.com/feed
    group: influencers
    priority: 10
    tags: [growth, product]
  - name: Notion Releases
    url: https://www.notion.com/releases/rss.xml
    group: company_changelogs
""",
        encoding="utf-8",
    )

    sources = load_sources(config_path)

    assert len(sources) == 2
    assert sources[0].name == "Lenny's Newsletter"
    assert sources[0].group == "influencers"
    assert sources[0].priority == 10
    assert sources[0].tags == ["growth", "product"]
    assert sources[1].priority == 0
    assert sources[1].tags == []


def test_load_sources_rejects_missing_required_fields(tmp_path: Path):
    config_path = tmp_path / "sources.yaml"
    config_path.write_text(
        """
sources:
  - name: Broken Source
    group: influencers
""",
        encoding="utf-8",
    )

    try:
        load_sources(config_path)
    except ValueError as exc:
        assert "url" in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing url")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_config.py -v
```

Expected: FAIL because `proradaar.config` is missing.

- [ ] **Step 3: Implement models and config**

Create `src/proradaar/models.py`:

```python
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
```

Create `src/proradaar/config.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from proradaar.models import Source


def load_sources(path: Path) -> list[Source]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    items = raw.get("sources")
    if not isinstance(items, list):
        raise ValueError("sources.yaml must contain a sources list")

    sources: list[Source] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"Source #{index + 1} must be an object")
        sources.append(_source_from_dict(item, index))
    return sources


def _source_from_dict(item: dict[str, Any], index: int) -> Source:
    for field_name in ("name", "url", "group"):
        if not item.get(field_name):
            raise ValueError(f"Source #{index + 1} is missing {field_name}")

    tags = item.get("tags", [])
    if tags is None:
        tags = []
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise ValueError(f"Source #{index + 1} tags must be a list of strings")

    return Source(
        name=str(item["name"]),
        url=str(item["url"]),
        group=str(item["group"]),
        priority=int(item.get("priority", 0)),
        tags=tags,
    )
```

- [ ] **Step 4: Create initial source list**

Create `sources.yaml`:

```yaml
sources:
  - name: Lenny's Newsletter
    url: https://www.lennysnewsletter.com/feed
    group: influencers
    priority: 10
    tags: [product, growth, activation]

  - name: Elena Verna
    url: https://elenaverna.substack.com/feed
    group: influencers
    priority: 10
    tags: [growth, monetisation, product]

  - name: Notion Releases
    url: https://www.notion.com/releases/rss.xml
    group: company_changelogs
    priority: 8
    tags: [collaboration, onboarding]

  - name: Asana Updates
    url: https://forum.asana.com/c/announcements/product-updates/70.rss
    group: company_changelogs
    priority: 7
    tags: [collaboration, workflow]

  - name: Atlassian Blog
    url: https://www.atlassian.com/blog/feed
    group: company_changelogs
    priority: 6
    tags: [enterprise, collaboration]

  - name: Miro Blog
    url: https://miro.com/blog/rss/
    group: company_changelogs
    priority: 6
    tags: [collaboration, activation]

  - name: HubSpot Product Updates
    url: https://www.hubspot.com/product-updates/rss.xml
    group: company_changelogs
    priority: 7
    tags: [crm, monetisation]

  - name: RB.RU
    url: https://rb.ru/feeds/all/
    group: industry_ru
    priority: 5
    tags: [russia, startups]

  - name: Product Hunt
    url: https://www.producthunt.com/feed
    group: industry_us
    priority: 4
    tags: [launches, products]
```

- [ ] **Step 5: Run tests**

Run:

```bash
pytest tests/test_config.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sources.yaml src/proradaar/models.py src/proradaar/config.py tests/test_config.py
git commit -m "feat: load digest source config"
```

---

### Task 3: PM Ranking And Deduplication

**Files:**
- Create: `src/proradaar/ranker.py`
- Create: `tests/test_ranker.py`

- [ ] **Step 1: Write ranking tests**

Create `tests/test_ranker.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_ranker.py -v
```

Expected: FAIL because `proradaar.ranker` is missing.

- [ ] **Step 3: Implement ranker**

Create `src/proradaar/ranker.py`:

```python
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from proradaar.models import FeedEntry, ScoredEntry


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
        hits = sum(1 for keyword in keywords if keyword in text)
        if hits:
            matched_topics.append(topic)
            score += hits * 3

    return ScoredEntry(entry=entry, score=score, matched_topics=matched_topics)


def _dedupe_key(entry: FeedEntry) -> str:
    if entry.url:
        return entry.url.rstrip("/").lower()
    normalized_title = re.sub(r"\W+", " ", entry.title.lower()).strip()
    return f"{entry.source.group}:{normalized_title}"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
```

- [ ] **Step 4: Run ranker tests**

Run:

```bash
pytest tests/test_ranker.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/proradaar/ranker.py tests/test_ranker.py
git commit -m "feat: rank product digest candidates"
```

---

### Task 4: Feed Fetching

**Files:**
- Create: `src/proradaar/fetcher.py`
- Create: `tests/test_fetcher.py`

- [ ] **Step 1: Write parser test**

Create `tests/test_fetcher.py`:

```python
from proradaar.fetcher import parse_feed
from proradaar.models import Source


def test_parse_feed_extracts_entries():
    source = Source(name="Example", url="https://example.com/feed", group="industry_us")
    xml = b"""<?xml version="1.0" encoding="UTF-8" ?>
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

    entries = parse_feed(source, xml)

    assert len(entries) == 1
    assert entries[0].title == "New onboarding flow"
    assert entries[0].url == "https://example.com/onboarding"
    assert entries[0].summary == "Setup improvements for new teams."
    assert entries[0].published_at is not None
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_fetcher.py -v
```

Expected: FAIL because `proradaar.fetcher` is missing.

- [ ] **Step 3: Implement feed parser and fetcher**

Create `src/proradaar/fetcher.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable

import feedparser
import httpx

from proradaar.models import FeedEntry, Source


def fetch_all(sources: Iterable[Source], timeout_seconds: float = 15.0) -> tuple[list[FeedEntry], list[str]]:
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
        title = str(item.get("title", "")).strip()
        url = str(item.get("link", "")).strip()
        summary = str(item.get("summary", item.get("description", ""))).strip()
        if not title or not url:
            continue
        entries.append(
            FeedEntry(
                source=source,
                title=title,
                url=url,
                published_at=_published_at(item),
                summary=summary,
            )
        )
    return entries


def _published_at(item: object) -> datetime | None:
    published = item.get("published") or item.get("updated")
    if published:
        try:
            value = parsedate_to_datetime(str(published))
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        except (TypeError, ValueError):
            return None
    return None
```

- [ ] **Step 4: Run fetcher tests**

Run:

```bash
pytest tests/test_fetcher.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/proradaar/fetcher.py tests/test_fetcher.py
git commit -m "feat: fetch and parse digest feeds"
```

---

### Task 5: LLM Prompt And Dry-Run Summarization

**Files:**
- Create: `src/proradaar/summarizer.py`
- Create: `tests/test_summarizer.py`

- [ ] **Step 1: Write prompt test**

Create `tests/test_summarizer.py`:

```python
from datetime import datetime, timezone

from proradaar.models import FeedEntry, ScoredEntry, Source
from proradaar.summarizer import build_prompt


def test_build_prompt_contains_pm_lens_and_links():
    source = Source(name="Lenny", url="https://example.com/feed", group="influencers")
    scored = [
        ScoredEntry(
            entry=FeedEntry(
                source=source,
                title="Activation lessons",
                url="https://example.com/post",
                published_at=datetime.now(timezone.utc),
                summary="Trial users reach activation faster with guided setup.",
            ),
            score=12,
            matched_topics=["activation", "onboarding"],
        )
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
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_summarizer.py -v
```

Expected: FAIL because `proradaar.summarizer` is missing.

- [ ] **Step 3: Implement prompt builder and LLM call**

Create `src/proradaar/summarizer.py`:

```python
from __future__ import annotations

from openai import OpenAI

from proradaar.models import ScoredEntry


def build_prompt(items: list[ScoredEntry], failures: list[str]) -> str:
    lines = [
        "Ты senior product manager. Составь ежедневный дайджест на русском.",
        "Фокус: SaaS, product management, onboarding, activation, monetisation.",
        "Не пересказывай все подряд. Выбери самое важное и объясни продуктовый смысл.",
        "Разделы: Influencers, Company Updates, Industry RU, Industry US, PM Lens, Watchlist.",
        "Для важных пунктов укажи источник, ссылку, факт, why it matters, PM angle.",
        "",
        "Candidate items:",
    ]
    for item in items:
        entry = item.entry
        lines.append(
            "\n".join(
                [
                    f"- Source: {entry.source.name}",
                    f"  Group: {entry.source.group}",
                    f"  Title: {entry.title}",
                    f"  URL: {entry.url}",
                    f"  Topics: {', '.join(item.matched_topics) or 'none'}",
                    f"  Score: {item.score}",
                    f"  Summary: {entry.summary[:700]}",
                ]
            )
        )

    if failures:
        lines.append("")
        lines.append("Source failures to mention briefly:")
        lines.extend(f"- {failure}" for failure in failures)

    return "\n".join(lines)


def summarize_with_llm(prompt: str, model: str) -> str:
    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You write concise product strategy digests for senior PMs.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content or ""
```

- [ ] **Step 4: Run summarizer tests**

Run:

```bash
pytest tests/test_summarizer.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/proradaar/summarizer.py tests/test_summarizer.py
git commit -m "feat: build product digest llm prompt"
```

---

### Task 6: Telegram Delivery

**Files:**
- Create: `src/proradaar/telegram.py`
- Create: `tests/test_telegram.py`

- [ ] **Step 1: Write message splitting test**

Create `tests/test_telegram.py`:

```python
from proradaar.telegram import split_telegram_message


def test_split_telegram_message_keeps_short_message_intact():
    assert split_telegram_message("hello", limit=10) == ["hello"]


def test_split_telegram_message_splits_on_line_boundaries():
    message = "line one\nline two\nline three"

    chunks = split_telegram_message(message, limit=15)

    assert chunks == ["line one", "line two", "line three"]


def test_split_telegram_message_splits_long_line():
    message = "abcdefghij"

    chunks = split_telegram_message(message, limit=4)

    assert chunks == ["abcd", "efgh", "ij"]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_telegram.py -v
```

Expected: FAIL because `proradaar.telegram` is missing.

- [ ] **Step 3: Implement Telegram helpers**

Create `src/proradaar/telegram.py`:

```python
from __future__ import annotations

import httpx


TELEGRAM_LIMIT = 3900


def split_telegram_message(message: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    chunks: list[str] = []
    current = ""

    for line in message.splitlines():
        if len(line) > limit:
            if current:
                chunks.append(current.rstrip())
                current = ""
            chunks.extend(line[index : index + limit] for index in range(0, len(line), limit))
            continue

        candidate = f"{current}\n{line}" if current else line
        if len(candidate) <= limit:
            current = candidate
        else:
            chunks.append(current.rstrip())
            current = line

    if current:
        chunks.append(current.rstrip())

    return chunks or [""]


def send_telegram_message(token: str, chat_id: str, message: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    with httpx.Client(timeout=15.0) as client:
        for chunk in split_telegram_message(message):
            response = client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": chunk,
                    "disable_web_page_preview": True,
                },
            )
            response.raise_for_status()
```

- [ ] **Step 4: Run Telegram tests**

Run:

```bash
pytest tests/test_telegram.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/proradaar/telegram.py tests/test_telegram.py
git commit -m "feat: add telegram digest delivery"
```

---

### Task 7: CLI Orchestration And Dry Run

**Files:**
- Create: `src/proradaar/digest.py`
- Create: `tests/test_digest.py`

- [ ] **Step 1: Write dry-run orchestration test**

Create `tests/test_digest.py`:

```python
from datetime import datetime, timezone

from proradaar.digest import build_digest
from proradaar.models import FeedEntry, Source


def test_build_digest_returns_ranked_prompt_input():
    source = Source(name="Example", url="https://example.com/feed", group="industry_us", priority=5)
    entries = [
        FeedEntry(
            source=source,
            title="New trial onboarding",
            url="https://example.com/onboarding",
            published_at=datetime.now(timezone.utc),
            summary="A launch about setup and activation.",
        )
    ]

    prompt = build_digest(entries, failures=[], max_items=10, recent_hours=36)

    assert "New trial onboarding" in prompt
    assert "senior product manager" in prompt
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_digest.py -v
```

Expected: FAIL because `proradaar.digest` is missing.

- [ ] **Step 3: Implement CLI**

Create `src/proradaar/digest.py`:

```python
from __future__ import annotations

import argparse
import os
from pathlib import Path

from proradaar.config import load_sources
from proradaar.fetcher import fetch_all
from proradaar.models import FeedEntry
from proradaar.ranker import deduplicate_entries, filter_recent, score_entries
from proradaar.summarizer import build_prompt, summarize_with_llm
from proradaar.telegram import send_telegram_message


def build_digest(
    entries: list[FeedEntry],
    failures: list[str],
    max_items: int,
    recent_hours: int,
) -> str:
    candidates = deduplicate_entries(entries)
    candidates = filter_recent(candidates, hours=recent_hours)
    scored = score_entries(candidates, limit=max_items)
    return build_prompt(scored, failures)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", default="sources.yaml")
    parser.add_argument("--max-items", type=int, default=40)
    parser.add_argument("--recent-hours", type=int, default=36)
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sources = load_sources(Path(args.sources))
    entries, failures = fetch_all(sources)
    prompt = build_digest(entries, failures, args.max_items, args.recent_hours)

    if args.dry_run:
        print(prompt)
        return

    digest = summarize_with_llm(prompt, args.model)
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    send_telegram_message(token, chat_id, digest)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests**

Run:

```bash
pytest -v
```

Expected: PASS.

- [ ] **Step 5: Run local dry-run**

Run:

```bash
python -m proradaar.digest --dry-run --max-items 10
```

Expected: prints a prompt with candidate items and links. Some source failures are acceptable during MVP setup.

- [ ] **Step 6: Commit**

```bash
git add src/proradaar/digest.py tests/test_digest.py
git commit -m "feat: orchestrate daily digest pipeline"
```

---

### Task 8: GitHub Actions Daily Run

**Files:**
- Create: `.github/workflows/daily-digest.yml`

- [ ] **Step 1: Create workflow**

Create `.github/workflows/daily-digest.yml`:

```yaml
name: Daily Product Digest

on:
  schedule:
    - cron: "30 4 * * *"
  workflow_dispatch:
    inputs:
      dry_run:
        description: "Print prompt instead of sending Telegram digest"
        type: boolean
        required: false
        default: false

jobs:
  digest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install
        run: python -m pip install -e ".[dev]"

      - name: Test
        run: pytest -v

      - name: Run digest
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          OPENAI_MODEL: ${{ vars.OPENAI_MODEL || 'gpt-4.1-mini' }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: |
          if [ "${{ github.event.inputs.dry_run }}" = "true" ]; then
            python -m proradaar.digest --dry-run
          else
            python -m proradaar.digest
          fi
```

The cron time `04:30 UTC` equals `07:30 Europe/Moscow`.

- [ ] **Step 2: Commit workflow**

```bash
git add .github/workflows/daily-digest.yml
git commit -m "ci: run product digest daily"
```

---

### Task 9: Launch And Verification

**Files:**
- Modify only if verification reveals failures.

- [ ] **Step 1: Push all commits**

Run:

```bash
git push
```

Expected: commits appear in `https://github.com/acc4apps24-ship-it/ProRadaar-main`.

- [ ] **Step 2: Configure GitHub secrets**

In GitHub repository settings, create:

```text
OPENAI_API_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

Optional repository variable:

```text
OPENAI_MODEL=gpt-4.1-mini
```

- [ ] **Step 3: Run local tests**

Run:

```bash
pytest -v
```

Expected: PASS.

- [ ] **Step 4: Run local dry-run**

Run:

```bash
python -m proradaar.digest --dry-run --max-items 10
```

Expected: prints a Russian-digest prompt candidate set without calling the LLM or Telegram.

- [ ] **Step 5: Run GitHub Actions dry-run**

Open the GitHub Actions tab, select `Daily Product Digest`, click `Run workflow`, and set `dry_run` to `true`.

Expected: workflow passes and logs show the prompt candidate set.

- [ ] **Step 6: Run GitHub Actions real delivery**

Open the same workflow, click `Run workflow`, and leave `dry_run` as `false`.

Expected: Telegram receives the final digest. If sources fail, the message includes a short technical note. If Telegram does not receive a message, inspect the `Run digest` step logs.

- [ ] **Step 7: Commit source URL fixes if needed**

If a feed URL returns 404, 403, or empty entries, edit `sources.yaml`, then run:

```bash
pytest -v
python -m proradaar.digest --dry-run --max-items 10
git add sources.yaml
git commit -m "fix: update digest source feeds"
git push
```

Expected: dry-run contains enough candidate items from working sources.

---

## Self-Review

- Spec coverage: the plan covers source config, RSS/Atom/Substack fetching, PM ranking, LLM summarization, Telegram delivery, GitHub Actions scheduling, cost caps, dry-run mode, source failure reporting, and verification.
- Scope check: the plan stays within the MVP. It does not add a dashboard, database, email delivery, multi-user support, paid scraping, or long-term analytics.
- Placeholder scan: no task depends on undefined "add later" work. Source feed URLs may require correction during Task 9, and that correction is explicitly covered.
- Type consistency: shared dataclasses are introduced before the modules that consume them.
