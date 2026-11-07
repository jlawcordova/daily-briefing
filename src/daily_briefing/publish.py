"""Build a static site + RSS feed of recent briefings for GitHub Pages.

Each deploy replaces the whole Pages site, so history is restored from the live site first:
`index.json` lists the published briefings and `briefings/<date>.md` holds each one. Nothing
is ever written to the repository.
"""

from __future__ import annotations

import html
import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path

import httpx
import markdown as md

from .models import Briefing
from .util import http_get

log = logging.getLogger(__name__)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FEED_TITLE = "Daily Briefing"
FEED_DESC = (
    "Davao weather, news, podcasts, AI-development articles, forums, and a Davao food pick, summarized by Claude."
)


@dataclass
class Entry:
    date: str
    title: str
    generated_at: str  # ISO 8601
    summary: str


# The renderer's only intentional HTML; everything else (feed titles, show notes) is escaped.
_ALLOWED_HTML = {
    "<p>&lt;details&gt;&lt;summary&gt;": "<details><summary>",
    "&lt;/summary&gt;</p>": "</summary>",
    "<p>&lt;/details&gt;</p>": "</details>",
}


def md_to_html(text: str) -> str:
    conv = md.Markdown(extensions=["tables", "sane_lists"], output_format="html")
    conv.preprocessors.deregister("html_block")
    conv.inlinePatterns.deregister("html")
    conv.inlinePatterns.deregister("entity")
    out = conv.convert(text)
    for k, v in _ALLOWED_HTML.items():
        out = out.replace(k, v)
    return re.sub(r'(href|src)="\s*(javascript|data|vbscript):[^"]*"', r'\1="#"', out, flags=re.I)


def entry_from_briefing(b: Briefing, markdown_text: str) -> Entry:
    total = sum(len(r.items) for rs in b.sections.values() for r in rs)
    first = markdown_text.splitlines()[0] if markdown_text else ""
    title = first.lstrip("# ").strip() or f"{FEED_TITLE} — {b.date}"
    counts = []
    for key, label in (("news", "news"), ("podcast", "podcasts"), ("article", "articles"), ("forum", "forum posts")):
        if key in b.sections:
            counts.append(f"{sum(len(r.items) for r in b.sections[key])} {label}")
    summary = f"{total} new items" + (f" ({', '.join(counts)})" if counts else "")
    feature = next((i for r in b.sections.get("feature", []) for i in r.items), None)
    if feature is not None:
        summary += f" · Feature: {getattr(feature, 'place_name', feature.title)}"
    if b.weather is not None:
        summary += f" · Weather: {b.weather.summary or b.weather.kind}, {b.weather.high}°/{b.weather.low}°C"
    return Entry(b.date, title, b.generated_at.isoformat(), summary)


def fetch_previous(client: httpx.Client, base_url: str) -> dict[str, tuple[Entry, str]]:
    """Return {date: (entry, markdown)} from the currently deployed site. Missing site -> {}."""
    base = base_url.rstrip("/")
    try:
        resp = client.get(f"{base}/index.json")
    except httpx.HTTPError as e:
        log.warning("could not reach %s: %s", base, e)
        return {}
    if resp.status_code == 404:
        log.info("no previous site at %s", base)
        return {}
    resp.raise_for_status()  # anything else is unexpected: fail rather than wipe history
    out: dict[str, tuple[Entry, str]] = {}
    for raw in resp.json().get("briefings", []):
        try:
            entry = Entry(**{k: raw[k] for k in ("date", "title", "generated_at", "summary")})
        except (KeyError, TypeError):
            continue
        if not DATE_RE.match(entry.date):
            continue
        try:
            text = http_get(client, f"{base}/briefings/{entry.date}.md").text
        except httpx.HTTPError as e:
            log.warning("dropping %s from history: %s", entry.date, e)
            continue
        out[entry.date] = (entry, text)
    return out


def load_new(out_dir: Path) -> dict[str, tuple[Entry, str]]:
    found: dict[str, tuple[Entry, str]] = {}
    for jp in sorted(out_dir.glob("briefing-*.json")):
        mp = jp.with_suffix(".md")
        if not mp.exists():
            continue
        b = Briefing.model_validate_json(jp.read_text(encoding="utf-8"))
        text = mp.read_text(encoding="utf-8")
        found[b.date] = (entry_from_briefing(b, text), text)
    return found


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="alternate" type="application/rss+xml" title="{feed_title}" href="{feed_url}">
<style>
body{{font:16px/1.55 system-ui,sans-serif;max-width:820px;margin:2rem auto;padding:0 1rem;color:#222}}
a{{color:#0b57d0}} table{{border-collapse:collapse}} td,th{{border:1px solid #ddd;padding:.25rem .5rem}}
blockquote{{margin:0 0 0 1rem;padding-left:.75rem;border-left:3px solid #ddd;color:#555}}
code{{background:#f3f3f3;padding:0 .2rem}} nav{{margin-bottom:1rem;font-size:.9rem}}
</style></head><body>
<nav><a href="{root}">All briefings</a> · <a href="{feed_url}">RSS</a>{extra_nav}</nav>
{body}
</body></html>
"""


def page(title: str, body: str, base: str, extra_nav: str = "") -> str:
    return PAGE.format(
        title=html.escape(title),
        feed_title=html.escape(FEED_TITLE),
        feed_url=f"{base}/feed.xml",
        root=f"{base}/",
        extra_nav=extra_nav,
        body=body,
    )


def rss(entries: list[tuple[Entry, str]], base: str) -> str:
    def cdata(s: str) -> str:
        return "<![CDATA[" + s.replace("]]>", "]]]]><![CDATA[>") + "]]>"

    items = []
    for e, text in entries:
        link = f"{base}/briefings/{e.date}.html"
        items.append(
            "<item>"
            f"<title>{html.escape(e.title)}</title>"
            f"<link>{link}</link>"
            f'<guid isPermaLink="true">{link}</guid>'
            f"<pubDate>{format_datetime(datetime.fromisoformat(e.generated_at))}</pubDate>"
            f"<description>{html.escape(e.summary)}</description>"
            f"<content:encoded>{cdata(md_to_html(text))}</content:encoded>"
            "</item>"
        )
    last = format_datetime(datetime.fromisoformat(entries[0][0].generated_at)) if entries else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" '
        'xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
        f"<title>{html.escape(FEED_TITLE)}</title>"
        f"<link>{base}/</link>"
        f"<description>{html.escape(FEED_DESC)}</description>"
        f'<atom:link href="{base}/feed.xml" rel="self" type="application/rss+xml"/>'
        + (f"<lastBuildDate>{last}</lastBuildDate>" if last else "")
        + "".join(items)
        + "</channel></rss>\n"
    )


def build_site(
    out_dir: Path,
    site_dir: Path,
    base_url: str,
    keep: int = 30,
    client: httpx.Client | None = None,
) -> list[Entry]:
    """Merge previously published briefings with new ones in `out_dir` and write the site."""
    base = base_url.rstrip("/")
    merged: dict[str, tuple[Entry, str]] = {}
    if client is not None:
        merged.update(fetch_previous(client, base))
    new = load_new(out_dir)
    if not new:
        raise FileNotFoundError(f"no briefing-*.json/.md pairs in {out_dir}")
    merged.update(new)  # a re-run on the same day replaces that day's briefing
    entries = sorted(merged.values(), key=lambda p: p[0].date, reverse=True)[:keep]

    (site_dir / "briefings").mkdir(parents=True, exist_ok=True)
    (site_dir / ".nojekyll").write_text("", encoding="utf-8")
    for e, text in entries:
        (site_dir / "briefings" / f"{e.date}.md").write_text(text, encoding="utf-8")
        raw = f' · <a href="{base}/briefings/{e.date}.md">Markdown</a>'
        (site_dir / "briefings" / f"{e.date}.html").write_text(
            page(e.title, md_to_html(text), base, raw), encoding="utf-8"
        )
    latest_entry, latest_text = entries[0]
    (site_dir / "latest.md").write_text(latest_text, encoding="utf-8")
    (site_dir / "feed.xml").write_text(rss(entries, base), encoding="utf-8")
    (site_dir / "index.json").write_text(
        json.dumps({"latest": latest_entry.date, "briefings": [asdict(e) for e, _ in entries]}, indent=2),
        encoding="utf-8",
    )
    rows = "\n".join(
        f'<li><a href="{base}/briefings/{e.date}.html">{html.escape(e.title)}</a> — {html.escape(e.summary)}</li>'
        for e, _ in entries
    )
    body = (
        f"<h1>{html.escape(FEED_TITLE)}</h1><p>{html.escape(FEED_DESC)}</p>"
        f'<p>Latest: <a href="{base}/latest.md">latest.md</a> · Feed: <a href="{base}/feed.xml">feed.xml</a></p>'
        f"<ul>{rows}</ul>"
    )
    (site_dir / "index.html").write_text(page(FEED_TITLE, body, base), encoding="utf-8")
    return [e for e, _ in entries]
