from __future__ import annotations

from openai import OpenAI

from proradaar.models import ScoredEntry


FOCUS_TOPICS = "SaaS, product management, onboarding, activation, monetisation"
REQUIRED_SECTIONS = (
    "Influencers",
    "Company Updates",
    "Industry RU",
    "Industry US",
    "PM Lens",
    "Watchlist",
)


def build_prompt(items: list[ScoredEntry], failures: list[str]) -> str:
    lines = [
        "Ты senior product manager. Составь ежедневный дайджест на русском.",
        "",
        f"Фокус: {FOCUS_TOPICS}.",
        (
            "Не пересказывай все подряд: выбери важное, объясни продуктовый смысл "
            "и практический PM angle."
        ),
        "",
        "Required sections:",
        *[f"- {section}" for section in REQUIRED_SECTIONS],
        "",
        (
            "For important items include: source, link, fact, why it matters, "
            "PM angle."
        ),
        "",
        "Items:",
    ]

    if items:
        for item in items:
            entry = item.entry
            source = entry.source
            lines.extend(
                [
                    f"- Source: {source.name}",
                    f"  Group: {source.group}",
                    f"  Title: {entry.title}",
                    f"  URL: {entry.url}",
                    f"  Topics: {', '.join(item.matched_topics)}",
                    f"  Score: {item.score}",
                    f"  Summary: {_truncate(entry.summary, 700)}",
                ]
            )
    else:
        lines.append("- No scored items available.")

    if failures:
        lines.extend(
            [
                "",
                "Source failures to mention briefly:",
                *[f"- {failure}" for failure in failures],
            ]
        )

    return "\n".join(lines)


def summarize_with_llm(prompt: str, model: str) -> str:
    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You write concise product strategy digests.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content or ""


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit]
