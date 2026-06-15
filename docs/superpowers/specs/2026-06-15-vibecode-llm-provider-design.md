# VibeCode LLM Provider Design

## Goal

Keep the existing Telegram digest delivery and replace the OpenAI summarization call with VibeCode AI Router when configured.

## Architecture

The digest pipeline stays the same: fetch sources, rank entries, build the prompt, summarize it, and send the result to Telegram. Only the summarization boundary changes.

`proradaar.summarizer` will expose the same `summarize_with_llm(prompt, model)` API, but internally choose a provider from `LLM_PROVIDER`. The code default remains OpenAI for backward compatibility. GitHub Actions defaults `LLM_PROVIDER` to `vibecode` so scheduled digests migrate without requiring an extra repository variable. When `LLM_PROVIDER=vibecode`, the OpenAI-compatible SDK will call VibeCode with `base_url=https://vibecode.bitrix24.tech/v1`, `api_key=VIBECODE_API_KEY`, and the model from `VIBECODE_MODEL` or the CLI/default model value.

## Configuration

- `LLM_PROVIDER`: optional. Supported values are `openai` and `vibecode`. Empty means `openai` in local code; GitHub Actions sets `vibecode` by default for this migration.
- `OPENAI_API_KEY`: required for OpenAI non-dry-run summaries.
- `OPENAI_MODEL`: optional OpenAI model, currently defaults to `gpt-4.1-mini`.
- `VIBECODE_API_KEY`: required when `LLM_PROVIDER=vibecode`.
- `VIBECODE_MODEL`: optional VibeCode model, defaulting in GitHub Actions to `bitrix/bitrixgpt-5.5`.

Telegram configuration remains unchanged:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Error Handling

The CLI should fail before making external LLM requests when required credentials are blank. Unknown `LLM_PROVIDER` values should raise a clear `RuntimeError`.

If LLM summarization fails after credentials are present, the existing behavior remains: send a Telegram failure message and re-raise the exception so GitHub Actions marks the run as failed.

## Testing

Unit tests will cover provider selection, VibeCode client configuration, missing VibeCode credentials, and unknown provider errors. Existing Telegram and digest tests remain valid.
