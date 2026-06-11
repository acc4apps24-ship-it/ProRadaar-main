# Telegram Rich Formatting Design

## Goal

Make the daily Telegram digest easier to scan by sending it with Telegram rich text formatting after the implementation is proven by tests.

The current plain-text path can be replaced on this feature branch after tests pass. The production-facing behavior should stay conservative: if the formatter receives text it does not recognize, it must still send a safe escaped message instead of dropping content.

## Recommended Approach

Use Telegram HTML parse mode instead of MarkdownV2.

HTML is easier to make safe for LLM-produced text because dynamic text can be escaped with Python's standard `html.escape`, while the application controls the small set of tags it emits. MarkdownV2 would require escaping many punctuation characters and would likely reintroduce the visual noise this change is meant to remove.

## Formatting Rules

The formatter should take the LLM digest string and produce Telegram-safe HTML:

- Recognized section headings are rendered in bold.
- Markdown-style heading markers such as `#`, `##`, or `###` are removed from display.
- Bullet markers are normalized to a simple bullet for readability.
- Markdown emphasis markers around phrases are converted to bold where simple and safe.
- Quote-like technical notes can be rendered as block quotes when they are already marked as quotes.
- All dynamic text is escaped before inserting HTML tags.

The formatter should not try to fully parse arbitrary Markdown. It should cover the digest patterns the prompt asks for and degrade gracefully for everything else.

## Telegram Delivery

`send_telegram_message` should split the source message first, format each chunk, and post chunks with `parse_mode` set to `HTML`.

Message splitting should continue to preserve source content and Telegram's size limit. Formatting each chunk after splitting avoids cutting HTML tags or entities across Telegram messages.

## Error Handling And Safety

The formatted path must be safe for special characters such as `<`, `>`, `&`, quotes, and URLs emitted by the LLM or sourced from feeds.

If a line is not recognized as a heading, bullet, or quote, it should be sent as escaped text. The implementation should avoid emitting unsupported or unbalanced HTML tags.

## Testing

Tests should cover:

- HTML escaping of special characters.
- Bold section headings.
- Removal of Markdown heading markers from display.
- Bullet normalization.
- Quote formatting for explicit quote lines.
- Telegram API payloads include `parse_mode: HTML`.
- Existing split and empty-message behavior remains intact.

## Definition Of Done

The change is done when:

- The new formatter is covered by failing-then-passing tests.
- Telegram sends HTML parse mode payloads.
- Existing Telegram splitting tests still pass.
- The full pytest suite passes in the isolated worktree.
