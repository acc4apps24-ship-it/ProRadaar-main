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
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
    )
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
