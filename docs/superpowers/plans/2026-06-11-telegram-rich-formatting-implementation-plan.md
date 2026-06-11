# Telegram Rich Formatting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the main Telegram digest delivery path with safe HTML-formatted messages after tests prove the behavior.

**Architecture:** Keep Telegram delivery in `src/proradaar/telegram.py`. Add a small formatter that converts common digest Markdown-like structure into Telegram HTML and escapes all dynamic text. Split source text before formatting each chunk so Telegram messages never cut HTML tags or entities across chunk boundaries.

**Tech Stack:** Python 3.12, standard-library `html` and `re`, `httpx`, `pytest`, Telegram Bot API HTML parse mode.

---

## File Structure

- Modify `src/proradaar/telegram.py`: add `format_telegram_digest_html`, internal line formatting helpers, and `parse_mode: HTML` payload support.
- Modify `tests/test_telegram.py`: add formatter tests and update Telegram payload expectations for HTML parse mode.

---

### Task 1: Formatter Behavior

**Files:**
- Modify: `tests/test_telegram.py`
- Modify: `src/proradaar/telegram.py`

- [ ] **Step 1: Write failing formatter tests**

Add these tests to `tests/test_telegram.py`:

```python
from proradaar.telegram import (
    format_telegram_digest_html,
    send_telegram_message,
    split_telegram_message,
)


def test_format_telegram_digest_html_bolds_known_headings_and_removes_markers():
    message = "## Company Updates:\n### PM Lens"

    assert format_telegram_digest_html(message) == (
        "<b>Company Updates</b>\n"
        "<b>PM Lens</b>"
    )


def test_format_telegram_digest_html_bolds_any_markdown_heading_marker():
    message = "## Market Signals & Strategy"

    assert format_telegram_digest_html(message) == (
        "<b>Market Signals &amp; Strategy</b>"
    )


def test_format_telegram_digest_html_escapes_special_characters():
    message = 'Company Updates\n- **Acme:** 5 < 7 & "quoted"'

    assert format_telegram_digest_html(message) == (
        "<b>Company Updates</b>\n"
        "• <b>Acme:</b> 5 &lt; 7 &amp; &quot;quoted&quot;"
    )


def test_format_telegram_digest_html_normalizes_bullets_and_quotes():
    message = "- One thing\n* Another thing\n> Source failures: A < B"

    assert format_telegram_digest_html(message) == (
        "• One thing\n"
        "• Another thing\n"
        "<blockquote>Source failures: A &lt; B</blockquote>"
    )
```

- [ ] **Step 2: Run formatter tests to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_telegram.py::test_format_telegram_digest_html_bolds_known_headings_and_removes_markers tests/test_telegram.py::test_format_telegram_digest_html_bolds_any_markdown_heading_marker tests/test_telegram.py::test_format_telegram_digest_html_escapes_special_characters tests/test_telegram.py::test_format_telegram_digest_html_normalizes_bullets_and_quotes -v
```

Expected: FAIL because `format_telegram_digest_html` is not defined.

- [ ] **Step 3: Implement the formatter**

Update `src/proradaar/telegram.py` with this behavior:

```python
import html
import re

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
        return f"<blockquote>{_format_inline_html(quote_match.group(1).strip())}</blockquote>"

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
```

- [ ] **Step 4: Run formatter tests to verify pass**

Run:

```bash
.venv/bin/python -m pytest tests/test_telegram.py::test_format_telegram_digest_html_bolds_known_headings_and_removes_markers tests/test_telegram.py::test_format_telegram_digest_html_bolds_any_markdown_heading_marker tests/test_telegram.py::test_format_telegram_digest_html_escapes_special_characters tests/test_telegram.py::test_format_telegram_digest_html_normalizes_bullets_and_quotes -v
```

Expected: PASS.

---

### Task 2: Telegram HTML Payload

**Files:**
- Modify: `tests/test_telegram.py`
- Modify: `src/proradaar/telegram.py`

- [ ] **Step 1: Update payload tests**

In `tests/test_telegram.py`, update `test_send_telegram_message_posts_each_chunk_in_order` expected payloads to include:

```python
"parse_mode": "HTML",
```

Add this new test:

```python
def test_send_telegram_message_formats_each_chunk_as_html(monkeypatch):
    requests = []
    real_client = httpx.Client

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, request=request)

    def client_factory(*, timeout):
        return real_client(transport=httpx.MockTransport(handler), timeout=timeout)

    monkeypatch.setattr("proradaar.telegram.httpx.Client", client_factory)

    send_telegram_message("token", "chat", "Company Updates\n- **Acme:** 5 < 7")

    assert requests == [
        {
            "chat_id": "chat",
            "text": (
                "<b>Company Updates</b>\n"
                "• <b>Acme:</b> 5 &lt; 7"
            ),
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
    ]
```

- [ ] **Step 2: Run payload test to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/test_telegram.py::test_send_telegram_message_formats_each_chunk_as_html -v
```

Expected: FAIL because `send_telegram_message` still sends plain text without `parse_mode`.

- [ ] **Step 3: Format chunks in sender**

Change the request payload in `send_telegram_message` so it formats each source chunk:

```python
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
```

- [ ] **Step 4: Run Telegram tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_telegram.py -v
```

Expected: PASS.

---

### Task 3: Full Verification

**Files:**
- Modify: `docs/superpowers/plans/2026-06-11-telegram-rich-formatting-implementation-plan.md`

- [ ] **Step 1: Run full test suite**

Run:

```bash
.venv/bin/python -m pytest
```

Expected: all tests pass.

- [ ] **Step 2: Review git diff**

Run:

```bash
git diff -- src/proradaar/telegram.py tests/test_telegram.py docs/superpowers/plans/2026-06-11-telegram-rich-formatting-implementation-plan.md
```

Expected: diff only contains Telegram rich formatting changes and this plan.
