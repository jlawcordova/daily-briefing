"""Hacker News collector using the official Firebase API."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from ..config import ForumSource
from ..models import ForumPost
from ..util import domain_of, http_get, keyword_match, strip_html
from .base import Context

API = "https://hacker-news.firebaseio.com/v0"
HN_ITEM = "https://news.ycombinator.com/item?id={id}"


def collect_hackernews(ctx: Context, source: ForumSource) -> list[ForumPost]:
    ids: list[int] = http_get(ctx.client, f"{API}/{source.feed}stories.json").json()[: source.scan_limit]

    def fetch(item_id: int) -> dict | None:
        try:
            return http_get(ctx.client, f"{API}/item/{item_id}.json").json()
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        raw = list(pool.map(fetch, ids))

    posts: list[ForumPost] = []
    for it in raw:
        if not it or it.get("dead") or it.get("deleted") or it.get("type") != "story":
            continue
        title = it.get("title") or ""
        points, comments = int(it.get("score") or 0), int(it.get("descendants") or 0)
        if points < source.min_points or comments < source.min_comments:
            continue
        if source.keywords and not keyword_match(title, source.keywords):
            continue
        hn_url = HN_ITEM.format(id=it["id"])
        url = it.get("url") or hn_url
        posts.append(
            ForumPost(
                id=f"hn:{it['id']}",
                source_name=source.name,
                title=title,
                url=url,
                published_at=datetime.fromtimestamp(it["time"], tz=UTC) if it.get("time") else None,
                author=it.get("by"),
                submitter=it.get("by"),
                source_description=strip_html(it.get("text"), limit=1200),
                points=points,
                comments=comments,
                comments_url=hn_url,
                domain=domain_of(url) if it.get("url") else None,
            )
        )
    # Keep the feed's ranking order (HN ranks by its own algorithm).
    return posts
