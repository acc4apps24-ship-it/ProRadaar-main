import httpx


TELEGRAM_LIMIT = 3900


def split_telegram_message(message: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    if limit < 1:
        raise ValueError("limit must be positive")
    if message == "":
        return [""]

    chunks: list[str] = []
    current = ""
    has_current = False

    for line in message.split("\n"):
        if len(line) > limit:
            if has_current:
                chunks.append(current)
                current = ""
                has_current = False
            chunks.extend(line[index : index + limit] for index in range(0, len(line), limit))
            continue

        if not has_current:
            current = line
            has_current = True
            continue

        candidate = f"{current}\n{line}"
        if len(candidate) <= limit:
            current = candidate
        else:
            chunks.append(current)
            current = line

    if has_current:
        chunks.append(current)

    return chunks


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
