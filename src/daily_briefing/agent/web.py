"""Agent-driven collector for sources without a feed (type: web)."""

from __future__ import annotations

from datetime import timedelta

from ..collectors.base import Context
from ..config import ArticleSource, NewsSource
from ..models import Article, Item
from ..util import domain_of, parse_date, same_site, strip_html, url_id
from .prompts import WEB_SUBMIT_TOOL, WEB_SYSTEM


def collect_web(ctx: Context, source: NewsSource | ArticleSource, category: str) -> list[Item]:
    if ctx.agent is None:
        raise RuntimeError("type: web sources need the Claude agent (ANTHROPIC_API_KEY)")
    url = str(source.url)
    domain = domain_of(url) or url
    days = source.lookback_days or ctx.settings.default_lookback_days
    start = (ctx.now - timedelta(days=days)).astimezone(ctx.settings.tz)
    end = ctx.now.astimezone(ctx.settings.tz)

    seen_titles = [v.get("title", "") for k, v in ctx.ledger.data["items"].items() if k.startswith(f"{category}:")][
        -50:
    ]
    system = WEB_SYSTEM.format(
        today=end.date().isoformat(),
        tz=ctx.settings.timezone,
        start=start.date().isoformat(),
        end=end.date().isoformat(),
        url=url,
        domain=domain,
    )
    user = f"Source: {source.name}\nIndex page: {url}\nAlready seen (titles): {seen_titles if seen_titles else 'none'}"
    tools = [
        {
            "type": "web_fetch_20250910",
            "name": "web_fetch",
            "max_uses": 12,
            "allowed_domains": [domain],
            "max_content_tokens": 20000,
        }
    ]
    result = ctx.agent.run_tools(system, user, tools, WEB_SUBMIT_TOOL, max_turns=10)

    items: list[Item] = []
    for raw in result.get("items", []):
        link, title = str(raw.get("url", "")), strip_html(raw.get("title"))
        if not link or not title or not same_site(link, url):
            continue  # reject off-domain or malformed results
        published = parse_date(raw.get("published_at"))
        if published is None or not (start.date() <= published.date() <= end.date()):
            continue  # agent dates must be inside the window
        items.append(
            Article(
                id=url_id(category, link),
                category=category,  # type: ignore[arg-type]
                source_name=source.name,
                title=title,
                url=link,
                published_at=published,
                author=raw.get("author"),
                source_description=strip_html(raw.get("description"), limit=1200),
                tags=["via agent"],
            )
        )
    return items
