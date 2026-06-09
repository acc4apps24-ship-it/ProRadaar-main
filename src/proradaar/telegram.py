import httpx


TELEGRAM_LIMIT = 3900


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


def send_telegram_message(token: str, chat_id: str, message: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    with httpx.Client(timeout=15.0) as client:
        for chunk in split_telegram_message(message):
            if not chunk:
                continue
            response = client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": chunk,
                    "disable_web_page_preview": True,
                },
            )
            response.raise_for_status()
