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
    name = _required_string(item, "name", index)
    url = _required_string(item, "url", index)
    group = _required_string(item, "group", index)

    priority = item.get("priority", 0)
    if isinstance(priority, bool) or not isinstance(priority, int):
        raise ValueError(f"Source #{index + 1} priority must be an integer")

    tags = item.get("tags", [])
    if tags is None:
        tags = []
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise ValueError(f"Source #{index + 1} tags must be a list of strings")

    source_type = item.get("type", "rss")
    if not isinstance(source_type, str) or not source_type.strip():
        raise ValueError(f"Source #{index + 1} type must be a non-empty string")

    exclude_keywords = item.get("exclude_keywords", [])
    if exclude_keywords is None:
        exclude_keywords = []
    if not isinstance(exclude_keywords, list) or not all(
        isinstance(keyword, str) for keyword in exclude_keywords
    ):
        raise ValueError(
            f"Source #{index + 1} exclude_keywords must be a list of strings"
        )

    return Source(
        name=name,
        url=url,
        group=group,
        priority=priority,
        tags=tags,
        source_type=source_type.strip(),
        exclude_keywords=[keyword.strip() for keyword in exclude_keywords],
    )


def _required_string(item: dict[str, Any], field_name: str, index: int) -> str:
    value = item.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Source #{index + 1} {field_name} must be a non-empty string"
        )
    return value.strip()
