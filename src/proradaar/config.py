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
