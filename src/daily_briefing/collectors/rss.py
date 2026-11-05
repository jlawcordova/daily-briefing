"""Generic RSS/Atom collector for news and article sources."""

from __future__ import annotations

from datetime import timedelta

import feedparser

from ..config import ArticleSource, NewsSource
from ..models import Article, Item
from ..util import clean_url, fallback_id, http_get, keyword_match, strip_html, struct_to_dt, url_id
from .base import Context, in_window


def fetch_feed(ctx: Context, url: str) -> feedparser.FeedParserDict:
    resp = http_get(ctx.client, url, headers={"Accept": "application/rss+xml, application/atom+xml, */*"})
    parsed = feedparser.parse(resp.content)
    if parsed.bozo and not parsed.entries:
        raise ValueError(f"could not parse feed at {url}: {parsed.get('bozo_exception')}")
    return parsed


def entry_date(entry) -> object:
    return struct_to_dt(entry.get("published_parsed") or entry.get("updated_parsed"))


def entry_image(entry) -> str | None:
    for key in ("media_thumbnail", "media_content"):
        media = entry.get(key)
        if media and isinstance(media, list) and media[0].get("url"):
            return media[0]["url"]
    for enc in entry.get("enclosures", []):
        if str(enc.get("type", "")).startswith("image/"):
            return enc.get("href")
    return None


def entry_description(entry) -> str | None:
    text = entry.get("summary")
    if not text and entry.get("content"):
        text = entry["content"][0].get("value")
    return strip_html(text, limit=1200)


def collect_rss(ctx: Context, source: NewsSource | ArticleSource, category: str) -> list[Item]:
    feed = fetch_feed(ctx, str(source.url))
    days = source.lookback_days or ctx.settings.default_lookback_days
    start, end = ctx.now - timedelta(days=days), ctx.now + timedelta(hours=1)
    include = getattr(source, "include_keywords", []) or []
    exclude = getattr(source, "exclude_keywords", []) or []

    items: list[Item] = []
    for e in feed.entries:
        link, title = e.get("link"), strip_html(e.get("title"))
        if not link or not title:
            continue
        published = entry_date(e)
        if not in_window(published, start, end):
            continue
        desc = entry_description(e)
        haystack = f"{title}\n{desc or ''}"
        if include and not keyword_match(haystack, include):
            continue
        if exclude and keyword_match(haystack, exclude):
            continue
        tags = [t.get("term") for t in e.get("tags", []) if t.get("term")]
        if published is None:
            tags.append("date unknown")
        item_id = url_id(category, link) if link else fallback_id(category, source.name, title, published)
        items.append(
            Article(
                id=item_id,
                category=category,  # type: ignore[arg-type]
                source_name=source.name,
                title=title,
                url=clean_url(link),
                published_at=published,
                author=e.get("author") or None,
                source_description=desc,
                image_url=entry_image(e),
                tags=tags[:8],
            )
        )
    return items
