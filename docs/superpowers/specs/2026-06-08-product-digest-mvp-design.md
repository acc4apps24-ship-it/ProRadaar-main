# Product Management and SaaS Digest MVP Design

## Goal

Build a low-cost daily digest that tracks product management and SaaS business updates across Russia and the US, with special attention to influencer writing and product launches from leading SaaS companies.

The digest should not be a generic news summary. It should interpret updates through a senior product manager lens, especially for:

- Onboarding
- Activation
- Monetisation

## MVP Scope

The MVP is a scheduled digest pipeline with no always-on server.

It runs once per day, collects items from configured sources, filters for relevant PM/SaaS signals, summarizes the strongest items with an LLM, and sends the digest to Telegram.

Email delivery, a web UI, source management UI, and long-term analytics are out of scope for the first version.

## Recommended Approach

Use a small Python script plus GitHub Actions:

1. GitHub Actions runs the digest on a daily cron.
2. A source config file defines RSS, Atom, Substack, and company update feeds.
3. The script fetches and normalizes feed entries.
4. A lightweight keyword classifier removes obvious noise before LLM usage.
5. The LLM receives only the top candidate items and produces a structured PM digest.
6. The script sends the final digest to Telegram via Bot API.

This keeps infrastructure simple and cheap. There is no server to host, and the main recurring cost is the LLM call volume.

## Components

### Source Config

File: `sources.yaml`

Defines source groups:

- `influencers`: Substack and blog feeds from product/growth thinkers such as Lenny Rachitsky and Elena Verna.
- `company_changelogs`: Product updates and changelogs from companies such as monday.com, Semrush, HubSpot, Notion, Asana, Atlassian, Miro, and similar SaaS leaders.
- `industry_ru`: Russian business, startup, product, and technology feeds.
- `industry_us`: US and global SaaS, product, growth, startup, and venture feeds.

Each source entry should include:

- `name`
- `url`
- `group`
- optional `priority`
- optional `tags`

### Fetcher

Fetches RSS and Atom feeds, including Substack `/feed` URLs where available.

Responsibilities:

- Read `sources.yaml`.
- Fetch feeds with timeouts.
- Parse entries into a shared internal shape.
- Preserve source name, group, title, URL, publication date, and summary/content snippet.
- Report source failures without stopping the full run.

### Normalizer And Deduplicator

Transforms all entries into one list and removes duplicates.

Deduplication should use:

- Canonical URL when available.
- Fallback title normalization for duplicate syndicated posts.

Only recent items should be considered for the daily digest. The MVP should default to entries from the last 36 hours so timezone and feed delay issues do not cause missed items.

### PM Relevance Classifier

Uses a cheap local rule-based filter before the LLM.

The filter should score items using keyword groups for:

- Onboarding: onboarding, setup, template, guide, getting started, import, migration, workspace, invite, signup, trial.
- Activation: activation, adoption, aha moment, engagement, workflow, automation, collaboration, retention, usage, user journey.
- Monetisation: pricing, billing, plan, upgrade, expansion, seats, limits, packaging, enterprise, freemium, trial, paywall.
- SaaS/product signal: product update, changelog, release, feature, launch, acquisition, integration, marketplace, AI feature, growth.

The classifier keeps a capped set of the highest-scoring candidates, grouped by source group.

The MVP should cap LLM input to a configurable daily limit, for example 30 to 50 items.

### LLM Summarizer

Produces the final digest in Russian.

The prompt should ask for analysis in the style of a senior product manager, not a journalist. The output should separate factual updates from interpretation.

Required sections:

- `Influencers`: notable essays or posts from product/growth operators.
- `Company Updates`: relevant launches and changelog items from SaaS leaders.
- `Industry RU`: Russian market/product/SaaS signals.
- `Industry US`: US/global market/product/SaaS signals.
- `PM Lens`: the most important takeaways across onboarding, activation, and monetisation.
- `Watchlist`: items worth watching over the next week.

For each important item, include:

- Source
- Link
- One-line factual summary
- Why it matters
- PM angle: onboarding, activation, monetisation, or other

### Telegram Delivery

Delivery uses Telegram Bot API.

Required secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `OPENAI_API_KEY` or another OpenAI-compatible provider key

The message should be concise enough for Telegram. If the digest exceeds the Telegram message limit, the sender should split it into multiple messages.

### Scheduler

GitHub Actions workflow:

- Runs daily on cron.
- Supports manual `workflow_dispatch`.
- Installs dependencies.
- Runs the digest script.

The default schedule should target morning delivery in Europe/Moscow, for example 07:30 Moscow time. The workflow should also support manual runs.

## Data Flow

```text
sources.yaml
  -> fetch feeds
  -> normalize entries
  -> deduplicate
  -> filter recent items
  -> score PM relevance
  -> cap candidate list
  -> LLM summarization
  -> Telegram delivery
```

## Error Handling

The MVP should keep running when individual sources fail.

Expected behavior:

- If one source fails, include it in a short technical note.
- If all sources fail, send a Telegram message saying the digest could not be generated.
- If the LLM call fails, send a short failure note with candidate count and failed step.
- If Telegram delivery fails, the GitHub Actions run should fail so the issue is visible in CI.

## Cost Controls

The MVP should minimize cost with:

- Local keyword scoring before LLM calls.
- A daily candidate cap.
- Short extracted snippets instead of full article text by default.
- One final summarization call per daily run.
- Optional source priority so high-signal sources beat low-signal ones when the cap is reached.

## Definition Of Done

The MVP is done when:

- A daily GitHub Actions workflow can run successfully.
- The repository contains a configurable source list.
- The pipeline fetches RSS/Atom/Substack feeds.
- The pipeline filters and ranks items related to onboarding, activation, and monetisation.
- The digest is written in Russian and framed for a senior product manager.
- Telegram receives one daily digest, split into multiple messages if needed.
- Failed sources are reported without breaking the full digest.
- LLM input volume is capped by configuration.

## Initial Source Strategy

Start with a small source list, then expand.

Initial influencer sources:

- Lenny Rachitsky / Lenny's Newsletter
- Elena Verna
- Additional product/growth Substacks can be added after the MVP works.

Initial company sources:

- monday.com
- Semrush
- HubSpot
- Notion
- Asana
- Atlassian
- Miro

Initial industry sources:

- Russian: RB.RU, vc.ru, Habr Product Management or related hubs.
- US/global: Product Hunt, SaaStr, OpenView, Reforge-style product/growth publications, and high-signal SaaS blogs with RSS.

Exact feed URLs can be refined during implementation. Sources that do not expose RSS can be supported later through RSSHub or RSS-Bridge.

Because the MVP has no database or persistent archive, occasional duplicate items are acceptable when feeds publish late or update timestamps shift. The 36-hour freshness window is intended to reduce missed items while keeping duplicates rare.

## Non-Goals

The MVP will not include:

- A dashboard or frontend.
- A database.
- Multi-user support.
- Email delivery.
- Persistent article archive.
- Paid source subscriptions or scraping behind authentication.
- Complex trend analytics across weeks.

## Testing And Verification

Testing should cover:

- Feed parsing with representative RSS and Atom examples.
- Deduplication behavior.
- PM keyword scoring.
- Telegram message splitting.
- Dry-run mode that prints the digest without sending it.

Manual verification:

- Run the workflow manually.
- Confirm Telegram delivery.
- Confirm the digest includes links and PM interpretation.
- Confirm source failures are visible but do not stop unrelated sources.

## Implementation Defaults

- Delivery channel: Telegram.
- Runtime: Python.
- Schedule: daily morning delivery in Europe/Moscow, plus manual workflow runs.
- Output language: Russian.
- LLM provider: OpenAI-compatible API configured through secrets.
