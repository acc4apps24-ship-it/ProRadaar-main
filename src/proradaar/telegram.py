import html
import re

import httpx


TELEGRAM_LIMIT = 3900
SECTION_HEADINGS = frozenset(
    {
        "Influencers",
        "Company Updates",
        "Industry RU",
        "Industry US",
        "PM Lens",
        "Watchlist",
    }
)
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+")
BULLET_RE = re.compile(r"^\s*(?:[-*•]\s+|\d+[.)]\s+)(.+)$")
QUOTE_RE = re.compile(r"^\s*>\s?(.*)$")
STRONG_RE = re.compile(r"(\*\*|__)(.+?)\1")


def split_telegram_message(message: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    if limit < 1:
        raise ValueError("limit must be positive")
    if message == "":
        return []

    chunks: list[str] = []
    current = ""

    for line in message.splitlines(keepends=True):
        remaining = line
        while remaining:
            available = limit - len(current)
            if len(remaining) <= available:
                current += remaining
                break

            if current:
                chunks.append(current)
                current = ""
                continue

            chunks.append(remaining[:limit])
            remaining = remaining[limit:]

    if current:
        chunks.append(current)

    return chunks


def format_telegram_digest_html(message: str) -> str:
    if message == "":
        return ""
    return "\n".join(_format_telegram_line(line) for line in message.split("\n"))


def _format_telegram_line(line: str) -> str:
    stripped = line.strip()
    if stripped == "":
        return ""

    quote_match = QUOTE_RE.match(line)
    if quote_match:
        quoted_text = _format_inline_html(quote_match.group(1).strip())
        return f"<blockquote>{quoted_text}</blockquote>"

    has_heading_marker = HEADING_RE.match(stripped) is not None
    heading_text = HEADING_RE.sub("", stripped).strip()
    heading_candidate = heading_text.rstrip(":").strip()
    if has_heading_marker or heading_candidate in SECTION_HEADINGS:
        return f"<b>{html.escape(heading_candidate, quote=True)}</b>"

    bullet_match = BULLET_RE.match(line)
    if bullet_match:
        return f"• {_format_inline_html(bullet_match.group(1).strip())}"

    return _format_inline_html(line)


def _format_inline_html(value: str) -> str:
    escaped = html.escape(value, quote=True)
    return STRONG_RE.sub(r"<b>\2</b>", escaped)


def send_telegram_message(token: str, chat_id: str, message: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    with httpx.Client(timeout=15.0) as client:
        for chunk in split_telegram_message(message):
            if not chunk:
                continue
            formatted_chunk = format_telegram_digest_html(chunk)
            response = client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": formatted_chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
            response.raise_for_status()
