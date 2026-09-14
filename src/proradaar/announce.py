from __future__ import annotations

import argparse
import os

from proradaar.telegram import send_telegram_message, send_telegram_poll


DEFAULT_POLL_QUESTION = "Как вам обновление ProRadaar?"
DEFAULT_POLL_OPTIONS = ["Супер", "Не одобряю"]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", required=True)
    parser.add_argument("--poll-question", default=DEFAULT_POLL_QUESTION)
    parser.add_argument("--no-poll", action="store_true")
    args = parser.parse_args(argv)

    token = _require_env("TELEGRAM_BOT_TOKEN")
    chat_id = _require_env("TELEGRAM_CHAT_ID")
    message = args.message.replace("\\n", "\n")

    send_telegram_message(token, chat_id, message)

    if not args.no_poll:
        send_telegram_poll(
            token,
            chat_id,
            args.poll_question,
            DEFAULT_POLL_OPTIONS,
        )


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required for announcement runs")
    return value


if __name__ == "__main__":
    main()
