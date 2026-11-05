"""Local food/café feature researched by the agent with web search."""

from __future__ import annotations

import logging
from datetime import timedelta
from urllib.parse import quote_plus

from ..collectors.base import Context
from ..config import FeatureSource
from ..models import Feature, FeatureSourceRef
from ..state import feature_key
from ..util import parse_date
from .client import AgentError
from .prompts import FEATURE_SUBMIT_TOOL, FEATURE_SYSTEM

log = logging.getLogger(__name__)


def validate_place(raw: dict, source: FeatureSource, ctx: Context) -> tuple[Feature | None, str | None]:
    name = (raw.get("place_name") or "").strip()
    if not name:
        return None, "missing place_name"
    if ctx.ledger.feature_seen(feature_key(name, source.location)):
        return None, f"{name} was already featured"

    today = ctx.today
    cutoff = today - timedelta(days=source.freshness_days)
    fresh: list[FeatureSourceRef] = []
    for s in raw.get("sources", []):
        d = parse_date(s.get("date"))
        if d and cutoff <= d.date() <= today and str(s.get("url", "")).startswith("http"):
            fresh.append(FeatureSourceRef(url=s["url"], title=s.get("title") or s["url"], date=d.date().isoformat()))
    if not fresh:
        return None, f"no source for {name} dated within the last {source.freshness_days} days"

    query = quote_plus(f"{name} {raw.get('address') or source.location}")
    map_url = f"https://www.google.com/maps/search/?api=1&query={query}"
    page = raw.get("website_or_page_url") or fresh[0].url
    return (
        Feature(
            id=f"feature:{feature_key(name, source.location)}",
            source_name=source.name,
            title=name,
            url=page,
            published_at=parse_date(max(s.date for s in fresh if s.date)),
            source_description=raw.get("description"),
            place_name=name,
            address=raw.get("address"),
            neighborhood=raw.get("neighborhood"),
            price_range=raw.get("price_range"),
            hours=raw.get("hours"),
            must_try=[m for m in raw.get("must_try", []) if m][:6],
            why_featured=raw.get("why_featured"),
            sources=fresh,
            map_url=map_url,
        ),
        None,
    )


def collect_feature(ctx: Context, source: FeatureSource) -> list[Feature]:
    if ctx.agent is None:
        raise RuntimeError("features need the Claude agent (ANTHROPIC_API_KEY)")
    today = ctx.today
    excluded = ctx.ledger.featured_names()
    rejections: list[str] = []
    features: list[Feature] = []

    for _attempt in range(2):
        system = FEATURE_SYSTEM.format(
            today=today.isoformat(),
            count=source.count - len(features),
            location=source.location,
            criteria=source.criteria or "(none)",
            freshness_days=source.freshness_days,
            cutoff=(today - timedelta(days=source.freshness_days)).isoformat(),
            excluded=", ".join(excluded + [f.place_name for f in features]) or "none",
        )
        user = f"Find today's {source.name} for {source.location}."
        if rejections:
            user += "\nYour previous answer was rejected: " + "; ".join(rejections) + ". Pick differently."
        tools = [
            {"type": "web_search_20250305", "name": "web_search", "max_uses": 8},
            {"type": "web_fetch_20250910", "name": "web_fetch", "max_uses": 8, "max_content_tokens": 15000},
        ]
        try:
            result = ctx.agent.run_tools(system, user, tools, FEATURE_SUBMIT_TOOL, max_turns=15)
        except AgentError as e:
            rejections.append(str(e))
            continue
        rejections = []
        for raw in result.get("places", []):
            feat, why = validate_place(raw, source, ctx)
            if feat:
                features.append(feat)
            else:
                rejections.append(why or "invalid")
        if len(features) >= source.count:
            break
    if not features and rejections:
        raise AgentError("; ".join(rejections))
    return features[: source.count]
