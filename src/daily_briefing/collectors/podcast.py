"""Podcast collector: resolves Apple Podcasts / website / feed URLs and parses episode metadata."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urljoin

import feedparser

from ..config import PodcastSource
from ..models import Episode, ShowInfo
from ..util import fallback_id, http_get, parse_duration, strip_html, struct_to_dt, url_id
from .base import Context, in_window

APPLE_ID_RE = re.compile(r"podcasts\.apple\.com/.*?/id(\d+)|itunes\.apple\.com/.*?/id(\d+)")
COMMON_FEED_PATHS = ("/feed", "/feed.xml", "/rss", "/rss.xml", "/podcast.xml", "/feed/podcast")


def apple_id(url: str) -> str | None:
    m = APPLE_ID_RE.search(url)
    return (m.group(1) or m.group(2)) if m else None


class _FeedLinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "link":
            return
        a = {k.lower(): (v or "") for k, v in attrs}
        if "alternate" in a.get("rel", "").lower() and a.get("type", "").lower() in (
            "application/rss+xml",
            "application/atom+xml",
        ):
            self.links.append(a.get("href", ""))


def discover_feed_links(html: str, base_url: str) -> list[str]:
    p = _FeedLinkParser()
    p.feed(html)
    return [urljoin(base_url, h) for h in p.links if h]


def _looks_like_feed(content: bytes) -> bool:
    head = content[:2000].lstrip().lower()
    return head.startswith(b"<?xml") or b"<rss" in head or b"<feed" in head


def resolve_feed(ctx: Context, source: PodcastSource) -> tuple[str, dict]:
    """Return (feed_url, itunes_metadata)."""
    url = str(source.url)
    meta: dict = {}
    if source.feed_url:
        return str(source.feed_url), meta

    aid = apple_id(url)
    if aid:
        resp = http_get(ctx.client, "https://itunes.apple.com/lookup", params={"id": aid, "entity": "podcast"})
        results = resp.json().get("results", [])
        if results:
            meta = results[0]
    cached = ctx.ledger.cached_feed(url)
    if cached:
        return cached, meta
    if meta.get("feedUrl"):
        return meta["feedUrl"], meta
    if aid:
        raise ValueError(f"iTunes lookup for id {aid} returned no feedUrl")

    resp = http_get(ctx.client, url)
    if _looks_like_feed(resp.content):
        return url, meta
    links = discover_feed_links(resp.text, str(resp.url))
    if links:
        return links[0], meta
    for path in COMMON_FEED_PATHS:
        candidate = urljoin(str(resp.url), path)
        try:
            r = http_get(ctx.client, candidate)
        except Exception:
            continue
        if _looks_like_feed(r.content):
            return candidate, meta
    raise ValueError(f"could not find an RSS feed for {url}")


def _int(v) -> int | None:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def _explicit(v) -> bool | None:
    # feedparser already maps itunes:explicit to True ("yes"), False ("clean"), or None.
    if v is None or isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("yes", "true", "explicit")


def collect_podcast(ctx: Context, source: PodcastSource) -> tuple[ShowInfo, list[Episode]]:
    feed_url, meta = resolve_feed(ctx, source)
    resp = http_get(ctx.client, feed_url)
    feed = feedparser.parse(resp.content)
    if feed.bozo and not feed.entries:
        raise ValueError(f"could not parse podcast feed {feed_url}")
    ctx.ledger.cache_feed(str(source.url), feed_url)

    f = feed.feed
    show = ShowInfo(
        name=source.name,
        feed_url=feed_url,
        website=f.get("link"),
        apple_url=meta.get("collectionViewUrl"),
        artwork_url=meta.get("artworkUrl600") or (f.get("image") or {}).get("href"),
        author=f.get("author") or meta.get("artistName"),
        genre=meta.get("primaryGenreName"),
    )

    start, end = source.window.bounds(ctx.now, ctx.settings.tz, ctx.settings.default_lookback_days)
    episodes: list[Episode] = []
    for e in feed.entries:
        title = strip_html(e.get("title"))
        if not title:
            continue
        published = struct_to_dt(e.get("published_parsed") or e.get("updated_parsed"))
        if not in_window(published, start, end):
            continue
        audio = next(
            (x.get("href") for x in e.get("enclosures", []) if str(x.get("type", "")).startswith("audio")),
            None,
        ) or next((x.get("href") for x in e.get("enclosures", [])), None)
        link = e.get("link") or audio or show.website or feed_url
        guid = e.get("id") or e.get("guid")
        if guid:
            item_id = f"podcast:{guid}" if len(guid) <= 200 else url_id("podcast", guid)
        elif audio:
            item_id = url_id("podcast", audio)
        else:
            item_id = fallback_id("podcast", source.name, title, published)

        notes = None
        if e.get("content"):
            notes = e["content"][0].get("value")
        notes = strip_html(notes or e.get("summary") or e.get("itunes_summary"), limit=2500)
        image = (e.get("image") or {}).get("href") if isinstance(e.get("image"), dict) else None

        episodes.append(
            Episode(
                id=item_id,
                source_name=source.name,
                show_name=source.name,
                title=title,
                url=link,
                published_at=published,
                author=e.get("author") or show.author,
                source_description=notes,
                image_url=image or show.artwork_url,
                tags=[t.get("term") for t in e.get("tags", []) if t.get("term")][:8],
                episode_number=_int(e.get("itunes_episode")),
                season=_int(e.get("itunes_season")),
                episode_type=e.get("itunes_episodetype"),
                duration_seconds=parse_duration(e.get("itunes_duration")),
                audio_url=audio,
                hosts=list(source.hosts),
                explicit=_explicit(e.get("itunes_explicit")),
                apple_url=show.apple_url,
            )
        )
    return show, episodes
