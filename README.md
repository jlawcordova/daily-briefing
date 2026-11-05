# daily-briefing

Scrapes the news, shows my favorite podcasts, and shares new relevant articles related to AI development, plus a
Davao City food/café pick. It runs daily in GitHub Actions, uses Claude to summarize, and publishes to GitHub Pages
as an RSS feed (plus a Markdown artifact).

- **Feed:** https://jlawcordova.com/daily-briefing/feed.xml (full briefing in each item)
- **Latest (Markdown):** https://jlawcordova.com/daily-briefing/latest.md
- **Archive:** https://jlawcordova.com/daily-briefing/ (last 30 days)

- **Why:** [`intent.md`](intent.md)
- **How:** [`spec.md`](spec.md)
- **What to collect:** [`config/briefing.yaml`](config/briefing.yaml)

## Setup (GitHub Actions)

1. Create a **private Gist** with a file `seen.json` containing `{"version":1,"items":{},"features":{},"feeds":{}}`.
2. Create a GitHub token with **only** the `gist` scope.
3. Add repository secrets: `ANTHROPIC_API_KEY`, `BRIEFING_GIST_ID` (the id in the Gist URL), `BRIEFING_GIST_TOKEN`.
4. Enable Pages: Settings → Pages → Source: **GitHub Actions**
   (or `gh api -X POST repos/OWNER/REPO/pages -f build_type=workflow`).
5. The **Daily Briefing** workflow runs at 06:00 Asia/Manila. To run it by hand: Actions → Daily Briefing → Run workflow
   (tick *dry run* to test without updating the ledger).
6. Read the briefing in the RSS feed / Pages site, the run's job summary, or the `briefing-N` artifact. Dry runs and
   `only` runs don't publish to Pages.

## Editing sources

Add an entry to `config/briefing.yaml`. For example, a podcast:

```yaml
podcasts:
  - name: My Show
    url: https://myshow.fm          # website, Apple Podcasts link, or RSS feed
    hosts: [Host One, Host Two]     # optional, keeps hosts out of the "guests" list
    window: { lookback_days: 7 }    # or { since: 2026-01-01, until: 2026-03-31 }
```

Check the config with `uv run python -m daily_briefing validate`.

## Local development

```bash
uv sync
uv run pytest
uv run python -m daily_briefing run --no-ai --dry-run            # no API key needed
ANTHROPIC_API_KEY=... uv run python -m daily_briefing run --dry-run
```

Without `BRIEFING_GIST_*` env vars, the seen ledger is stored in `.state/seen.json`.
