# Spec: Daily Briefing

See `intent.md` for the reasons behind this. This document describes **how** it works.

---

## 1. Overview

```
config/briefing.yaml ──► Collectors (deterministic fetch) ──► Dedup filter ──► Claude agent
                                   │                        (ledger from Gist)  (enrich, summarize,
                                   └── fallback: agent with web tools ◄──────────  fallback fetch, feature)
                                                                                     │
                                         output/briefing-YYYY-MM-DD.md ◄── Renderer ◄┘
                                                    │
                                    Actions artifact + GitHub Pages RSS feed + ledger written back to Gist
```

**Design principle: a hybrid pipeline.** Anything with a structured source (RSS/Atom, the iTunes Lookup API, the HN API) is fetched deterministically in code. This is cheap and reliable. Claude is used for:
1. **Enrichment**: writing summaries and "why it matters" notes, and tagging items.
2. **Fallback collection**: for sources with no feed (`type: web`). The agent uses `web_fetch` and `web_search` to pull the latest items out of HTML.
3. **The feature**: researching a Davao City food/café place, which needs web search and judgement.

## 2. Tech stack

| Concern | Choice |
|---|---|
| Language | Python 3.12 |
| LLM | Anthropic Messages API via the `anthropic` SDK (v2). Default model `claude-sonnet-5-5`, configurable |
| Agent tools | Server tools `web_search_20250305` and `web_fetch_20250910`, plus strict "submit" output tools (§8) |
| Feeds | `feedparser` |
| HTTP | `httpx` |
| HTML → text | `trafilatura` (article body extraction for summarization context) |
| Config validation | `pydantic` v2 |
| YAML | `pyyaml` |
| Tests | `pytest` with recorded fixtures (no network in CI tests) |
| Packaging | `uv` / `pyproject.toml` |

## 3. Repository layout

```
.
├── config/
│   └── briefing.yaml          # user-editable source config
├── src/daily_briefing/
│   ├── __main__.py            # CLI entrypoint: `python -m daily_briefing`
│   ├── config.py              # pydantic models + loader
│   ├── models.py              # Item, Episode, Article, ForumPost, Feature
│   ├── state.py               # seen-ledger load/save/prune (Gist or local file backend)
│   ├── pipeline.py            # collect → dedup → bodies → feature → enrich → render
│   ├── util.py                # HTTP, URL normalization/ids, dates, text helpers
│   ├── collectors/
│   │   ├── base.py            # shared Context
│   │   ├── rss.py             # generic RSS/Atom (news, blogs)
│   │   ├── podcast.py         # resolves iTunes/website URL → feed, parses episode metadata
│   │   ├── hackernews.py      # HN Firebase API
│   │   └── body.py            # trafilatura text extraction (summary context, reading time)
│   ├── agent/
│   │   ├── client.py          # Anthropic wrapper: strict tools, tool loop, cost + budget
│   │   ├── prompts.py         # prompt templates + output tool schemas
│   │   ├── enrich.py          # batch summarization
│   │   ├── web.py             # agent-driven collector for feedless sites (type: web)
│   │   └── feature.py         # Davao food feature research
│   └── render/
│       └── markdown.py        # Markdown renderer (plain Python, no template engine)
├── tests/                     # pytest, fixtures, fake Anthropic client
├── .github/workflows/
│   ├── daily-briefing.yml     # scheduled run
│   └── ci.yml                 # lint + tests on PRs
├── intent.md
├── spec.md
└── README.md
```

## 4. Configuration (`config/briefing.yaml`)

### 4.1 Schema

```yaml
version: 1

settings:
  timezone: Asia/Manila            # used for "today", date windows, and rendering
  model: claude-sonnet-5-5
  thinking: between_tools          # between_tools | adaptive | omit (omit for models older than Sonnet 5.5)
  effort: medium                   # low | medium | high | null
  pricing:                         # optional, only for models missing from the built-in price table
    input_per_mtok: 2.0
    output_per_mtok: 10.0
    cache_read_multiplier: 0.05
  max_items_per_source: 10         # hard cap after filtering
  default_lookback_days: 2         # used when a source does not set its own window
  summary_length: short            # short (1–2 sentences) | medium (one paragraph)
  dedup_retention_days: 120        # ledger entries older than this are pruned
  budget:
    max_usd_per_run: 1.00          # agent stops enrichment and marks items "unsummarized" past this

news:
  - name: string                   # required, display name
    type: rss | web                # default rss
    url: string                    # feed URL (rss) or page URL (web)
    fetch_body: bool               # default false (news is often paywalled); extract article text for context
    lookback_days: int             # optional
    max_items: int                 # optional, overrides settings
    enabled: bool                  # default true

podcasts:
  - name: string
    url: string                    # Apple Podcasts URL | show website | direct RSS feed
    feed_url: string               # optional, skips resolution if given
    hosts: [string]                # optional, regular hosts, so the agent can tell hosts apart from guests
    window:                        # optional, one of:
      lookback_days: int           #   relative window ending now
      # since: 2025-01-01          #   or absolute bounds (inclusive, ISO dates)
      # until: 2025-12-31
    max_items: int
    enabled: bool

articles:
  - name: string
    type: rss | web
    url: string
    lookback_days: int
    include_keywords: [string]     # optional, keep only items matching any keyword (title/description)
    exclude_keywords: [string]
    fetch_body: bool               # default true
    enabled: bool

forums:
  - name: string
    type: hackernews               # extensible: reddit, lobsters, discourse ...
    feed: top | best | new | ask | show   # HN list
    min_points: int                # optional filter
    min_comments: int
    keywords: [string]             # optional, keep only matching posts (whole-word, title)
    scan_limit: int                # how many stories from the HN list to inspect (default 100)
    fetch_body: bool               # default true, extract the linked article for context
    max_items: int
    enabled: bool

features:
  - name: string
    type: local_food
    location: string               # e.g. "Davao City, Philippines"
    freshness_days: 365            # sources must be updated within this window
    count: 1                       # how many places per briefing
    criteria: string               # free-text guidance for the agent
    enabled: bool

weather:                           # optional, one place
  name: Weather                    # default "Weather", shown in the run report
  place: string                    # e.g. "Davao City"
  lat: float
  lon: float
  link: string                     # optional, the place's yr.no forecast page
  enabled: bool
```

Validation happens at startup with pydantic. An invalid config fails the run with a clear error message before any API calls are made.

### 4.2 Initial config

```yaml
version: 1

settings:
  timezone: Asia/Manila
  model: claude-sonnet-5-5
  thinking: between_tools
  effort: medium
  max_items_per_source: 10
  default_lookback_days: 2
  summary_length: short
  dedup_retention_days: 120
  budget:
    max_usd_per_run: 1.00

news:
  - name: BBC News – Top Stories
    type: rss
    url: https://feeds.bbci.co.uk/news/rss.xml
  - name: BBC News – Technology
    type: rss
    url: https://feeds.bbci.co.uk/news/technology/rss.xml
  - name: The New York Times – Home Page
    type: rss
    url: https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml
  - name: The New York Times – Technology
    type: rss
    url: https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml

podcasts:
  - name: Syntax – Tasty Treats for Web Developers
    url: https://syntax.fm                        # website → feed auto-discovered (https://feed.syntax.fm)
    hosts: [Wes Bos, Scott Tolinski, CJ Reynolds]
    window: { lookback_days: 7 }
  - name: Soft Skills Engineering
    url: https://softskills.audio                 # website → feed auto-discovered (/feed.xml)
    window: { lookback_days: 7 }

articles:
  - name: claude.dev – Tips, tricks, and POVs from Anthropic's developers
    type: rss
    url: https://claude.dev/rss.xml
    lookback_days: 30              # posts every week or two; dedup prevents repeats
  - name: OpenAI News
    type: rss
    url: https://openai.com/news/rss.xml
    lookback_days: 7

forums:
  - name: Hacker News – Top
    type: hackernews
    feed: top
    min_points: 100
    max_items: 15
  - name: Hacker News – AI
    type: hackernews
    feed: top
    keywords: [AI, LLM, Claude, Anthropic, OpenAI, GPT, agent, model]
    min_points: 30
    max_items: 10

features:
  - name: Davao Food & Café Pick
    type: local_food
    location: Davao City, Philippines
    freshness_days: 365
    count: 1
    criteria: >
      A well-regarded café or restaurant that is currently operating, with at least
      one review, article, or social post from the last 12 months. Prefer local or
      independent spots. Include what to order, price range, address, and hours if available.
```

## 5. Data model

All collected items share one base shape. Fields left empty in the source are `null`, never invented.

```python
class Item:
    id: str                 # stable dedup key (see §7)
    category: Literal["news", "podcast", "article", "forum", "feature"]
    source_name: str
    title: str
    url: str
    published_at: datetime | None
    author: str | None
    source_description: str | None   # description/summary as given by the source (HTML stripped)
    image_url: str | None
    tags: list[str]
    # agent-generated
    ai_summary: str | None           # agent's short description
    ai_why_it_matters: str | None    # one line, optional
    ai_tags: list[str]

class Episode(Item):
    show_name: str
    episode_number: int | None
    season: int | None
    duration_seconds: int | None
    audio_url: str | None            # enclosure
    guests: list[str]                # extracted by the agent from title/description
    explicit: bool | None
    apple_url: str | None

class Article(Item):
    reading_time_min: int | None     # estimated from extracted body
    body_excerpt: str | None         # first ~600 chars of extracted text (context for summary)

class ForumPost(Item):
    points: int
    comments: int
    comments_url: str
    submitter: str
    domain: str | None

class Feature(Item):
    place_name: str
    address: str | None
    neighborhood: str | None
    price_range: str | None          # e.g. "₱200–₱500 per person"
    hours: str | None
    must_try: list[str]
    sources: list[{url, title, date}]  # evidence, each must be inside freshness_days
    map_url: str | None
```

## 6. Collection

### 6.1 RSS collector (news, articles, podcasts)
- Fetch with `httpx` (timeout 20s, 2 retries with backoff, descriptive User-Agent).
- Parse with `feedparser`. Normalize dates to the configured timezone.
- Window filter: keep entries where `published_at` falls inside the window. Entries with no date are kept only if their id has not been seen before, and they are marked "date unknown".
- Apply keyword filters, then cap at `max_items`.

### 6.2 Podcast URL resolution
In order:
1. If `feed_url` is set, use it.
2. **Apple Podcasts URL**: extract `id\d+`, call `https://itunes.apple.com/lookup?id=<id>&entity=podcast`, and use `feedUrl`. Also keep the artwork, genre, and `collectionViewUrl` as show metadata.
3. **Show website**: GET the page and look for `<link rel="alternate" type="application/rss+xml">`. If none is found, try common paths (`/feed`, `/feed.xml`, `/rss`, `/rss.xml`, `/podcast.xml`, `/feed/podcast`). If none works, the source fails with a clear error and you can set `feed_url` by hand.
4. **Direct feed**: if the URL already parses as RSS, use it.

The resolved feed URL is cached in the ledger under `feeds` so resolution doesn't repeat every day.

If `hosts` is set, the agent leaves those names out of `guests` and treats them as regular hosts. An episode with only hosts (for example a Syntax "Hasty Treat") gets `guests: []`.

Episode fields come from iTunes/podcast namespace tags: `itunes:duration`, `itunes:episode`, `itunes:season`, `itunes:explicit`, `enclosure`, `itunes:summary` / `content:encoded` / `description`.

### 6.3 Hacker News collector
- List IDs: `https://hacker-news.firebaseio.com/v0/{feed}stories.json`.
- Item details: `/v0/item/{id}.json`, fetched concurrently (limit about 30 lookups per list).
- Filters: `min_points`, `min_comments`, case-insensitive whole-word `keywords` on the title.
- Optional enrichment: fetch the linked article and extract the body with trafilatura as context for the summary. Skipped for PDFs and video.

### 6.4 Web (agent) collector, for `type: web`
The agent gets the page URL, the window, and a strict JSON output schema. It uses `web_fetch` to read the index page, picks the posts inside the window, and fetches each post page to confirm the date and get a description. It returns `[{title, url, published_at, author, source_description}]`.
- URLs the agent returns must belong to the source's domain. Anything else is discarded.
- The titles of up to 50 recently seen items from the same category are passed to the agent so it can skip them. Dedup runs again afterward anyway.
- If this collector fails, the error is recorded and the run continues.

### 6.5 Feature collector (`local_food`)
The agent uses `web_search` and `web_fetch` with the `criteria`. Hard requirements, validated in code after the agent returns:
- At least 1 source with a date inside `freshness_days` (for example a blog post, news article, or recent review).
- The place name is not in the ledger's `features` list, so the same place is never featured twice.
- Output must match the `Feature` schema. A malformed result gets 1 retry; after that the section shows "No feature today" with the reason.

### 6.6 Weather collector

Deterministic, no AI. One GET to MET Norway's Locationforecast `compact` API
(`https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=..&lon=..`, the forecast behind yr.no;
free, no key, needs the identifying User-Agent the client already sends). It keeps the hourly steps on
today's local date and folds them into a `Weather`: `place`, `date`, `high` and `low` (°C, rounded),
`precipitation_mm`, `summary` (by morning 06–12, afternoon 12–18 and evening 18–24, like "Clear morning,
showers in the afternoon and evening") and `kind`, the sky the Daily Brief page draws.

`kind` is one of `sun`, `fair`, `partly`, `cloudy`, `fog`, `drizzle`, `showers`, `rain`, `heavy-rain`,
`thundershowers`, `storm`. Each hour's yr.no symbol (`_day`/`_night` dropped) maps to one: `clearsky` sun,
`fair` fair, `partlycloudy` partly, `cloudy`, `fog`, `lightrain` drizzle, `rain`, `heavyrain` and
`heavyrainshowers` heavy-rain, `lightrainshowers`/`rainshowers` showers, `*showersandthunder` thundershowers,
`*rainandthunder` storm (sleet and snow map onto the rain of the same strength). The day's kind comes from
06:00–18:00: no wet hours gives the most common dry kind (a tie goes cloudier); wet half the day or more gives
storm (2+ thunder hours), heavy-rain (3+ heavy hours), drizzle (mostly light) or rain; fewer wet hours give
thundershowers (any thunder), heavy-rain (2+ heavy hours), drizzle (all light) or showers.

The weather is a line at the top of the Markdown (so it is in every feed item), a row in the run report,
`weather` in the briefing JSON, and a "Weather: …" note in the archive summary. A failure is reported and
the rest of the run carries on.

## 7. Deduplication

**Ledger:** a `seen.json` file stored in a **private GitHub Gist**. This keeps the daily state changes out of the repo's history.

- **Backend selection:** if `BRIEFING_GIST_ID` and `BRIEFING_GIST_TOKEN` are set, the Gist backend is used. Otherwise a local file is used (`.state/seen.json`, git-ignored), which is the setup for local development.
- **Read:** at the start of the run, `GET https://api.github.com/gists/{id}` and parse `files["seen.json"].content`. If the file is truncated (larger than about 1 MB), fetch it from `raw_url` instead. If the Gist is missing or empty, start with an empty ledger and log a warning.
- **Write:** `PATCH https://api.github.com/gists/{id}` with the updated `seen.json`. This happens only in the `commit-state` step (§10).
- **Token:** a fine-grained or classic PAT with **only** the `gist` scope, stored as the repo secret `BRIEFING_GIST_TOKEN`. The Gist id is stored as the secret `BRIEFING_GIST_ID`.
- **Setup (one time):** create a private Gist containing a `seen.json` file with the content `{"version":1,"items":{},"features":{},"feeds":{}}`, then copy its id from the URL.
- **Concurrency:** the workflow `concurrency` group keeps runs from overlapping, so there are no conflicting writes.
- **History:** the Gist's own revision history is a free audit trail and makes rollback easy.

File shape:

```json
{
  "version": 1,
  "items": { "<id>": { "first_seen": "2025-11-05", "category": "podcast", "title": "..." } },
  "features": { "<normalized place name>|davao city": "2025-11-05" },
  "feeds": { "<podcast url>": "<resolved feed url>" }
}
```

**ID strategy** (first available wins):
1. Podcast: the feed `guid`, else the enclosure URL.
2. HN: `hn:<item id>`.
3. Everything else: the canonical URL, normalized (lowercase host, `utm_*`/`ref`/`fbclid` params stripped, trailing slash removed, `http`→`https`). Hashed with sha1 and prefixed by category.
4. Fallback: sha1 of `source_name + title + published date`.

**Rules:**
- Items whose id is already in the ledger are dropped before enrichment, so no tokens are spent on them.
- Items are written to the ledger only after the briefing renders and the artifact uploads. A failed run does not use up items, and the next run will retry them.
- Entries older than `dedup_retention_days` are pruned. This is safe because the date windows are much shorter than the retention period. Feature entries are never pruned.
- A `--dry-run` flag renders without writing the ledger. A `--ignore-seen` flag exists for debugging.
- Ordering and limits: each source keeps its newest unseen items up to `max_items`. Items that the limit cuts today and that are still inside the window can appear tomorrow. That's fine, because they have never been shown.

## 8. Agent (Claude) usage

- **Auth:** the `ANTHROPIC_API_KEY` env var, from a GitHub secret.
- **Enrichment:** items are batched per category (up to about 15 per call). Each item is sent with its title, source description, and an excerpt of up to about 1,500 chars. The agent returns JSON `[{id, ai_summary, ai_why_it_matters, ai_tags, guests?}]`, validated with pydantic. If validation fails, the batch is retried once, and after that the items are left unsummarized.
- **Prompt rules:** summarize only from the provided text, never invent facts, say "insufficient information" when context is thin, and keep the configured length.
- **Structured output (Sonnet 5.5 compatible):** each task has a "submit" tool (`submit_summaries`, `submit_items`, `submit_feature`). These tools are sent with `strict: true`, and every object gets `additionalProperties: false`; nullable fields use `anyOf` with null, and all fields are required. `tool_choice` is always `auto`, because Sonnet 5.5 returns a 400 for `any` or `tool`. The prompt tells the model to call the submit tool. If it doesn't, the loop sends a reminder, and close to `max_turns` it says "You are out of steps".
- **Thinking and effort:** `thinking: {type: between_tools}` and `output_config: {effort: medium}` by default, both configurable. Use `thinking: omit` and `effort: null` for older models. Content blocks are read by type, and `thinking` blocks are passed back unchanged.
- **Tool use loop:** standard agentic loop. Server tools run on Anthropic's side, and `pause_turn` is handled by resending. `max_turns` is 10 for web sources and 15 for the feature. `stop_reason: refusal` is reported as an error for that source.
- **Prompt caching:** system prompts and tool definitions are marked `cache_control` to cut cost across batches.
- **Cost accounting:** input/output, cache write/read tokens and web searches ($10 per 1,000) are tracked per call. A built-in price table covers current models (Sonnet 5.5: $2/$10 per MTok, cache reads 0.05×). For other models set `settings.pricing`. Once `max_usd_per_run` is reached, remaining items are rendered without AI summaries and the briefing shows a note saying so.

## 9. Output

### 9.1 File
`output/briefing-YYYY-MM-DD.md` (date in the configured timezone), plus `output/briefing-YYYY-MM-DD.json`, which holds the same data in machine-readable form.

### 9.2 Markdown layout

```markdown
# Daily Briefing — Wednesday, 5 November 2025
_Generated 06:00 Asia/Manila · 42 new items · est. cost $0.18_

## Contents
- [News](#news) (14) · [Podcasts](#podcasts) (2) · [Articles](#articles) (3) · [Forums](#forums) (15) · [Feature](#feature)

## 🗞 News
### BBC News – Top Stories
#### [Headline](https://...)
- **Published:** 2025-11-05 04:12 PHT
- **Source summary:** <feed description>
- **AI summary:** <1–2 sentences>
- **Why it matters:** <one line>

## 🎧 Podcasts
### Syntax – Tasty Treats for Web Developers
#### [Episode title](https://...)
| | |
|---|---|
| Published | 2025-11-04 |
| Duration | 1h 12m |
| Episode | S2 · E45 |
| Guests | Jane Doe |
| Listen | [Audio](...) · [Apple Podcasts](...) |

**AI summary:** ...
<details><summary>Show notes (from the episode)</summary>

...original description...
</details>

## 📝 Articles
...same shape as news, plus author and reading time...

## 💬 Forums
### Hacker News – Top
1. **[Title](url)** (domain.com) · ▲ 412 · 💬 [188 comments](hn link) · by user · 5h ago
   > AI summary...

## 🍽 Feature: Davao Food & Café Pick
### <Place name>
- **Address / area:** ... · [Map](...)
- **Price range:** ... · **Hours:** ...
- **Must try:** ...
- **Why it's featured:** <agent paragraph>
- **Sources (last 12 months):** [Title — 2025-08-14](url), ...

---
## Run report
| Source | Status | Fetched | New | Notes |
|---|---|---|---|---|
| BBC News – Top Stories | ✅ | 38 | 9 | |
| Soft Skills Engineering | ⚠️ | 0 | 0 | feed timeout |
```

Sections with no new items show "Nothing new since the last briefing."

## 10. GitHub Actions

`.github/workflows/daily-briefing.yml` (see the file for the full version). Steps:

1. Checkout, `astral-sh/setup-uv`, `uv sync --frozen --no-dev`.
2. **Check secrets**: fail early with a clear error if any of the three secrets is missing.
3. **Generate briefing**: `python -m daily_briefing run --config config/briefing.yaml --out output`, plus `--dry-run` / `--only` from the `workflow_dispatch` inputs.
4. **Job summary**: the Markdown is also added to the run's summary page so it can be read without downloading.
5. **Upload artifact** `briefing-<run number>` containing `briefing-*.md` and `briefing-*.json`, kept for 90 days.
6. **Publish to GitHub Pages** (skipped for dry/partial runs): `python -m daily_briefing publish --base-url <pages url>`
   builds `site/` and `actions/deploy-pages` deploys it. Because a deploy replaces the whole site, `publish` first reads
   the live `index.json` and downloads each earlier `briefings/<date>.md`, then rebuilds the archive (last 30) around
   today's briefing (a same-day re-run replaces that day). The site contains `feed.xml` (RSS 2.0, full HTML in
   `content:encoded`), `latest.md`, `index.html`, `index.json`, and `briefings/<date>.{md,html}`. Raw HTML from sources
   is escaped. Nothing is written to the repository.
7. **Save seen ledger to Gist**: `commit-state`, only if everything above succeeded, it isn't a dry run, and `--only` wasn't used. A partial run is treated as a test.

Triggers: `schedule: "0 22 * * *"` (06:00 Asia/Manila) and `workflow_dispatch`. `permissions: contents: read, pages: write, id-token: write`; the job runs in the `github-pages` environment. A `concurrency` group keeps runs from overlapping.

**Required repo secrets:** `ANTHROPIC_API_KEY`, `BRIEFING_GIST_ID`, `BRIEFING_GIST_TOKEN`.

The ledger write in §7 happens in a final CLI step, `python -m daily_briefing commit-state`, which runs only after the upload and Pages deploy succeed. The `run` step writes the new ids to `output/.pending-seen.json`, and `commit-state` merges them into the Gist ledger. This keeps the "consume only after the artifact is uploaded" rule true.

Also: `ci.yml` runs `ruff check`, `ruff format --check`, `pytest`, and `validate` on PRs and pushes to main.

## 11. CLI

```
python -m daily_briefing run [--config PATH] [--out DIR] [--dry-run] [--commit] [--ignore-seen]
                             [--only news,podcasts,articles,forums,features] [--no-ai]
python -m daily_briefing commit-state [--config PATH] [--pending output/.pending-seen.json]
python -m daily_briefing publish --base-url URL [--out output] [--site site] [--keep 30] [--no-history]
python -m daily_briefing validate [--config PATH]
```

- `--no-ai`: runs without Claude, with no summaries, `type: web` sources, or feature. No API key is needed. Useful locally.
- `--commit`: saves the ledger right after rendering, for local use. CI uses the separate `commit-state` step instead.

Local development: `uv sync`, then `uv run python -m daily_briefing run --no-ai --commit`. Without the Gist env vars, the ledger is `.state/seen.json`.

```
```

## 12. Error handling and limits
- Each source is isolated: an exception is logged and added to the Run report, and the run continues.
- The run fails (non-zero exit) only if the config is invalid, the API key is missing, or **every** source failed.
- Network: 20s timeout, 2 retries with backoff, at most 8 concurrent requests per pool. `type: web` pages are fetched by Anthropic's server-side `web_fetch` tool, limited to the source's domain through `allowed_domains`.
- Agent-produced dates and URLs are validated in code (URLs must parse and stay on the source domain; dates must fall inside the window).

## 13. Testing
- Unit: config validation, URL normalization and id generation, window filtering, ledger prune and commit, iTunes URL parsing, Markdown rendering (snapshot).
- Collectors: recorded feed and API fixtures, no live network.
- Agent: a fake Anthropic client that returns canned tool-use responses. Covered: strict schema checks, no forced `tool_choice`, the thinking/effort settings, refusal handling, budget stop, and feature/web validation.
- Pipeline: end-to-end run with mocked HTTP and Claude, including dedup across two runs, a failing source, and `--no-ai`.

## 14. Milestones
All 8 milestones are implemented. The live Claude path still needs to be confirmed by the first real CI run.

1. Skeleton, config models, `validate` command, the initial `briefing.yaml`.
2. RSS collector, dedup ledger (local file plus Gist backends), Markdown renderer (no AI yet), so news, claude.dev, and OpenAI work end to end.
3. Podcast resolution (website auto-discovery and iTunes) with full episode metadata, for Syntax and Soft Skills Engineering.
4. Hacker News collector.
5. Claude enrichment (summaries, why-it-matters, guests vs. hosts) with budget tracking.
6. Davao food feature (agent with `web_search` / `web_fetch`).
7. GitHub Actions workflow, Gist state commit, artifact upload.
8. Web agent collector for future feedless sources.

## 15. Decisions
| Topic | Decision |
|---|---|
| Podcasts | Syntax (syntax.fm; hosts Wes Bos, Scott Tolinski, CJ Reynolds) and Soft Skills Engineering (softskills.audio). Both feeds were confirmed to auto-discover from the website. |
| "Claude.dev" | `https://claude.dev` ("Sharing tips, tricks, and POVs from Anthropic's developers"). It has an RSS feed at `/rss.xml`, so no agent scraping is needed. |
| Schedule | Daily at 06:00 Asia/Manila (`cron: 0 22 * * *` UTC). |
| Dedup ledger storage | Private GitHub Gist (§7). |
| Delivery | RSS feed + static archive on GitHub Pages (artifacts need a GitHub sign-in, so Claude couldn't read them). Also the Actions artifact and job summary. |
| Default model | `claude-sonnet-5-5`. `claude-sonnet-4-5` reaches end-of-life on 2026-11-30, so it isn't used. |
| Web tool versions | Basic `web_search_20250305` / `web_fetch_20250910`. The newer "dynamic filtering" versions run code on the API side and make costs harder to predict, so they aren't used. |

Note: the initial config has no `type: web` sources, because every source has a feed. The web agent collector (§6.4) is still part of the design for future feedless sources, but it moves to a later milestone.
