# VibeCode LLM Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add VibeCode AI Router as an OpenAI-compatible LLM provider while keeping Telegram delivery unchanged.

**Architecture:** Keep the digest pipeline intact and route only the summarization call based on `LLM_PROVIDER`. Reuse the OpenAI SDK with a custom `base_url` for VibeCode.

**Tech Stack:** Python 3.12, OpenAI Python SDK, pytest, GitHub Actions.

---

### Task 1: Add Provider-Aware Summarization

**Files:**
- Modify: `src/proradaar/summarizer.py`
- Test: `tests/test_summarizer.py`

- [ ] **Step 1: Write failing tests**

Add tests that patch `proradaar.summarizer.OpenAI` and assert that `LLM_PROVIDER=vibecode` creates the client with `api_key` from `VIBECODE_API_KEY` and `base_url=https://vibecode.bitrix24.tech/v1`. Add tests for missing `VIBECODE_API_KEY` and unknown providers.

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_summarizer.py -v`

Expected: new tests fail because provider routing does not exist yet.

- [ ] **Step 3: Implement provider routing**

In `src/proradaar/summarizer.py`, add:

```python
VIBECODE_BASE_URL = "https://vibecode.bitrix24.tech/v1"

def _llm_provider() -> str:
    return os.environ.get("LLM_PROVIDER", "openai").strip().lower() or "openai"

def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required for { _llm_provider() } summaries")
    return value

def _build_client(provider: str) -> OpenAI:
    if provider == "openai":
        return OpenAI()
    if provider == "vibecode":
        return OpenAI(api_key=_require_env("VIBECODE_API_KEY"), base_url=VIBECODE_BASE_URL)
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")
```

Update `summarize_with_llm` to call `_build_client(_llm_provider())`.

- [ ] **Step 4: Run summarizer tests**

Run: `pytest tests/test_summarizer.py -v`

Expected: all summarizer tests pass.

### Task 2: Wire VibeCode Environment Into CLI and GitHub Actions

**Files:**
- Modify: `src/proradaar/digest.py`
- Modify: `.github/workflows/daily-digest.yml`
- Test: `tests/test_digest.py`

- [ ] **Step 1: Write failing digest tests**

Add tests that set `LLM_PROVIDER=vibecode`, `VIBECODE_API_KEY`, and `VIBECODE_MODEL`, then assert the digest CLI passes the VibeCode model to `summarize_with_llm` and still sends Telegram messages.

- [ ] **Step 2: Implement model selection**

In `src/proradaar/digest.py`, make the default model provider-aware:

```python
def _default_model() -> str:
    provider = os.environ.get("LLM_PROVIDER", "openai").strip().lower()
    if provider == "vibecode":
        return os.environ.get("VIBECODE_MODEL", "bitrix/bitrixgpt-5.5")
    return os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
```

Use `_default_model()` as the `--model` default.

- [ ] **Step 3: Update GitHub Actions env**

In `.github/workflows/daily-digest.yml`, add:

```yaml
LLM_PROVIDER: ${{ vars.LLM_PROVIDER || 'vibecode' }}
VIBECODE_API_KEY: ${{ secrets.VIBECODE_API_KEY }}
VIBECODE_MODEL: ${{ vars.VIBECODE_MODEL || 'bitrix/bitrixgpt-5.5' }}
```

Keep existing OpenAI env values for fallback.

- [ ] **Step 4: Run focused tests**

Run: `pytest tests/test_digest.py tests/test_summarizer.py -v`

Expected: all focused tests pass.

### Task 3: Full Verification and Commit

**Files:**
- Verify all changed files.

- [ ] **Step 1: Run full test suite**

Run: `pytest -v`

Expected: all tests pass.

- [ ] **Step 2: Inspect git diff**

Run: `git diff -- .github/workflows/daily-digest.yml src/proradaar/digest.py src/proradaar/summarizer.py tests/test_digest.py tests/test_summarizer.py`

Expected: diff only contains VibeCode provider support and tests.

- [ ] **Step 3: Commit and push**

Run:

```bash
git add .github/workflows/daily-digest.yml src/proradaar/digest.py src/proradaar/summarizer.py tests/test_digest.py tests/test_summarizer.py docs/superpowers/specs/2026-06-15-vibecode-llm-provider-design.md docs/superpowers/plans/2026-06-15-vibecode-llm-provider-implementation-plan.md
git commit -m "feat: add VibeCode LLM provider"
git push origin main
```
