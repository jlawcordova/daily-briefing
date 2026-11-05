"""Batch summarization of collected items."""

from __future__ import annotations

import json
import logging

from ..models import Episode, Item
from .client import Agent, AgentError, BudgetExceeded
from .prompts import ENRICH_SYSTEM, ENRICH_TOOL, LENGTHS, NO_GUESTS, PODCAST_GUESTS

log = logging.getLogger(__name__)
BATCH_SIZE = 15


def _payload(item: Item) -> dict:
    d: dict = {
        "id": item.id,
        "source": item.source_name,
        "title": item.title,
        "published": item.published_at.date().isoformat() if item.published_at else None,
        "source_description": (item.source_description or "")[:1500] or None,
    }
    if item.body_excerpt:
        d["article_excerpt"] = item.body_excerpt[:1500]
    if isinstance(item, Episode):
        d["show_hosts"] = item.hosts
    return d


def enrich_items(agent: Agent, items: list[Item], summary_length: str) -> tuple[int, str | None]:
    """Fill ai_* fields in place. Returns (n_enriched, stop_reason_or_None)."""
    if not items:
        return 0, None
    done = 0
    # Group by category so each batch uses the right prompt.
    groups: dict[str, list[Item]] = {}
    for it in items:
        groups.setdefault(it.category, []).append(it)

    for category, group in groups.items():
        guests = PODCAST_GUESTS if category == "podcast" else NO_GUESTS
        system = ENRICH_SYSTEM.format(length=LENGTHS[summary_length], guests=guests)
        for i in range(0, len(group), BATCH_SIZE):
            batch = group[i : i + BATCH_SIZE]
            by_id = {it.id: it for it in batch}
            user = "Items:\n" + json.dumps([_payload(it) for it in batch], ensure_ascii=False, indent=1)
            result = None
            for attempt in range(2):
                try:
                    result = agent.structured(system, user, ENRICH_TOOL)
                    if isinstance(result.get("items"), list):
                        break
                    result = None
                except BudgetExceeded as e:
                    return done, str(e)
                except AgentError as e:
                    log.warning("enrichment batch failed (attempt %d): %s", attempt + 1, e)
            if not result:
                continue
            for entry in result["items"]:
                it = by_id.get(str(entry.get("id")))
                if not it or not entry.get("summary"):
                    continue
                it.ai_summary = entry["summary"].strip()
                it.ai_why_it_matters = (entry.get("why_it_matters") or "").strip() or None
                it.ai_tags = [str(t).lower() for t in entry.get("tags", [])][:4]
                if isinstance(it, Episode) and isinstance(entry.get("guests"), list):
                    hosts = {h.lower() for h in it.hosts}
                    it.guests = [g for g in entry["guests"] if g and g.lower() not in hosts]
                done += 1
    return done, None
