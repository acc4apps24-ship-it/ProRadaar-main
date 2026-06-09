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
    prompt, _candidate_count = _build_digest_context(
        entries,
        failures,
        max_items,
        recent_hours,
    )
    return prompt


def _build_digest_context(
    entries: list[FeedEntry],
    failures: list[str],
    max_items: int,
    recent_hours: int,
) -> tuple[str, int]:
    candidates = deduplicate_entries(entries)
    candidates = filter_recent(candidates, hours=recent_hours)
    scored = score_entries(candidates, limit=max_items)
    return build_prompt(scored, failures), len(candidates)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", default="sources.yaml")
    parser.add_argument("--max-items", type=int, default=40)
    parser.add_argument("--recent-hours", type=int, default=36)
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    sources = load_sources(Path(args.sources))
    entries, failures = fetch_all(sources)
    prompt, candidate_count = _build_digest_context(
        entries,
        failures,
        args.max_items,
        args.recent_hours,
    )

    if args.dry_run:
        print(prompt)
        return

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    if not entries and failures:
        send_telegram_message(token, chat_id, _all_sources_failed_message(failures))
        return

    try:
        digest = summarize_with_llm(prompt, args.model)
    except Exception as exc:
        send_telegram_message(
            token,
            chat_id,
            _llm_failed_message(candidate_count, exc),
        )
        raise

    send_telegram_message(token, chat_id, digest)


def _all_sources_failed_message(failures: list[str]) -> str:
    return (
        "Digest could not be generated: no feed entries were fetched. "
        f"Source failures: {_failure_note(failures)}"
    )


def _llm_failed_message(candidate_count: int, exc: Exception) -> str:
    return (
        "Digest generation failed during LLM summarization. "
        f"Candidate count: {candidate_count}. Error: {exc}"
    )


def _failure_note(failures: list[str], limit: int = 240) -> str:
    note = "; ".join(failures[:3])
    if len(note) <= limit:
        return note
    return f"{note[: limit - 3]}..."


if __name__ == "__main__":
    main()
