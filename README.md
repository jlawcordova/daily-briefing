# daily-briefing

Scrapes the news, shows my favorite podcasts, and shares new relevant articles related to AI development, plus a
Davao City food/café pick and today's Davao weather (MET Norway, the forecast behind yr.no). It runs daily in GitHub Actions, uses Claude to summarize, and publishes to GitHub Pages
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

## Art (Pixpocket)

The Daily Brief page's pixel art is drawn here with [Pixpocket](https://github.com/pixpocket/pixpocket), in
`art/daily-brief.pixpocket` (a Pixpocket document: its palette, objects and scenes). The library is generated:
`art/generators/` draws it with the 2:1 isometric kit in `art/kit/`, so edit the generators, not the JSON.

Pixpocket is pinned in [`.pixpocket-version`](.pixpocket-version) (0.21.0). Install that release into `.tools/`
(it needs `gh`, signed in with access to pixpocket/pixpocket):

```bash
scripts/install-pixpocket.sh
```

Then build, check and publish the art (stdlib Python only):

```bash
python3 art/generators/build.py               # or --no-publish to skip the SVGs
```

It writes the objects and scenes into the document, runs `pixpocket check` and the 2:1 ruler, then
`pixpocket publish --dir art/build/svg`, and `art/generators/smil.py` turns their CSS frame loops into SMIL in
`art/build/smil/` (gitignored). Those are the files the page is given, as its own published files under `spot/`
and not in its asset store, which strips an SVG's `<style>` and `<animate>`.

**The spot of the day** is three stacked layers, so any food goes on any table under any light:

- `brief-light-<color>`: a sky of twelve rays turning behind the table, cream near the food, in `blue`, `teal`,
  `plum`, `gold`, `sunset` or `green`.
- `brief-table-<table>`: `grill` (a samgyupsal table, a charcoal grill with pork belly and banchan, smoke rising),
  `cafe` (a marble bistro table, a bud vase), `fine` (a white cloth, a candle that flickers, a glass of wine) or
  `wood` (a cozy plank table, a gingham placemat).
- `brief-food-<food>`: `coffee`, `dumplings`, `noodle-soup`, `pasta`, `ice-cream`, `skewers`, `bread`, `cake`,
  `rice-bowl`, `burger` or `pizza`, with the glints that twinkle on it. No faces; each served the way it comes.

`brief-<food>` scenes put each food on its usual table, to look at
(`pixpocket render scene:brief-coffee --scale 3 --out x.png`, run in `art/`). The page takes the spot's `food`,
`table` and `light` fields when it has them, else picks from the spot's words (a Korean grill, a café, fine
dining), the food's usual table and a light kept per place.
