"""Orchestrates collect → dedup → enrich → feature → render."""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from .agent.client import Agent, BudgetExceeded
from .agent.enrich import enrich_items
from .agent.feature import collect_feature
from .agent.web import collect_web
from .collectors.base import Context
from .collectors.body import enrich_bodies
from .collectors.hackernews import collect_hackernews
from .collectors.podcast import collect_podcast
from .collectors.rss import collect_rss
from .config import BriefingConfig
from .models import Briefing, Category, Feature, Item, SourceResult
from .render.markdown import render_markdown
from .state import Ledger, feature_key

log = logging.getLogger(__name__)

PENDING_FILE = ".pending-seen.json"


@dataclass
class Task:
    category: Category
    source: object
    fn: Callable[[], list[Item]]
    needs_agent: bool = False
    fetch_body: bool = False


@dataclass
class RunOutput:
    briefing: Briefing
    markdown_path: Path
    json_path: Path
    pending_path: Path
    all_failed: bool


def build_tasks(cfg: BriefingConfig, ctx: Context, only: set[str] | None) -> list[Task]:
    tasks: list[Task] = []

    def want(cat: str) -> bool:
        return not only or cat in only

    if want("news"):
        for s in cfg.news:
            if s.enabled:
                fn = (
                    (lambda s=s: collect_web(ctx, s, "news"))
                    if s.type == "web"
                    else (lambda s=s: collect_rss(ctx, s, "news"))
                )
                tasks.append(Task("news", s, fn, needs_agent=s.type == "web", fetch_body=s.fetch_body))
    if want("podcasts"):
        for s in cfg.podcasts:
            if s.enabled:
                tasks.append(Task("podcast", s, lambda s=s: collect_podcast(ctx, s)))  # returns (show, eps)
    if want("articles"):
        for s in cfg.articles:
            if s.enabled:
                fn = (
                    (lambda s=s: collect_web(ctx, s, "article"))
                    if s.type == "web"
                    else (lambda s=s: collect_rss(ctx, s, "article"))
                )
                tasks.append(Task("article", s, fn, needs_agent=s.type == "web", fetch_body=s.fetch_body))
    if want("forums"):
        for s in cfg.forums:
            if s.enabled:
                tasks.append(Task("forum", s, lambda s=s: collect_hackernews(ctx, s), fetch_body=s.fetch_body))
    return tasks


def _run_task(task: Task, ctx: Context) -> SourceResult:
    res = SourceResult(name=task.source.name, category=task.category)  # type: ignore[attr-defined]
    if task.needs_agent and ctx.agent is None:
        res.status, res.notes = "skipped", "needs AI agent (disabled)"
        return res
    try:
        out = task.fn()
        if task.category == "podcast":
            res.show, items = out  # type: ignore[misc]
        else:
            items = out
        res.items = list(items)
        res.fetched = len(res.items)
    except BudgetExceeded as e:
        res.status, res.notes = "warn", str(e)
    except Exception as e:
        log.exception("source %s failed", res.name)
        res.status, res.notes = "error", f"{type(e).__name__}: {e}"[:300]
    return res


def run_briefing(
    cfg: BriefingConfig,
    ledger: Ledger,
    out_dir: Path,
    *,
    agent: Agent | None,
    client: httpx.Client,
    ignore_seen: bool = False,
    only: set[str] | None = None,
    now: datetime | None = None,
) -> RunOutput:
    settings = cfg.settings
    now = now or datetime.now(UTC)
    ctx = Context(client=client, settings=settings, ledger=ledger, now=now, agent=agent)
    today = ctx.today

    # 1. Collect. Deterministic sources run concurrently; agent-driven ones run sequentially.
    tasks = build_tasks(cfg, ctx, only)
    plain = [t for t in tasks if not t.needs_agent]
    agentic = [t for t in tasks if t.needs_agent]
    with ThreadPoolExecutor(max_workers=8) as pool:
        plain_results = list(pool.map(lambda t: _run_task(t, ctx), plain))
    agent_results = [_run_task(t, ctx) for t in agentic]
    by_task = dict(zip([id(t) for t in plain + agentic], plain_results + agent_results, strict=True))
    results = [(t, by_task[id(t)]) for t in tasks]  # preserve config order

    # 2. Dedup (ledger + within this run), sort, cap.
    run_seen: set[str] = set()
    body_items: list[Item] = []
    for task, res in results:
        fresh = []
        for it in res.items:
            if it.id in run_seen or (not ignore_seen and ledger.seen(it.id)):
                continue
            run_seen.add(it.id)
            fresh.append(it)
        if task.category != "forum":
            fresh.sort(key=lambda i: i.published_at or datetime.min.replace(tzinfo=UTC), reverse=True)
        cap = getattr(task.source, "max_items", None) or settings.max_items_per_source
        res.items = fresh[:cap]
        res.new = len(res.items)
        if task.fetch_body:
            body_items += res.items

    # 3. Readable-text context for summaries / reading time.
    if body_items:
        enrich_bodies(client, body_items)

    # 4. Feature (agent + web search).
    feature_results: list[SourceResult] = []
    if not only or "features" in only:
        for fs in [f for f in cfg.features if f.enabled]:
            fr = SourceResult(name=fs.name, category="feature")
            if agent is None:
                fr.status, fr.notes = "skipped", "needs AI agent (disabled)"
            else:
                try:
                    fr.items = list(collect_feature(ctx, fs))
                    fr.fetched = fr.new = len(fr.items)
                except Exception as e:
                    log.exception("feature %s failed", fs.name)
                    fr.status, fr.notes = "error", f"{type(e).__name__}: {e}"[:300]
            feature_results.append(fr)

    # 5. Enrich with Claude.
    budget_hit = False
    all_items = [it for _, r in results for it in r.items]
    if agent is not None and all_items:
        _, stop = enrich_items(agent, all_items, settings.summary_length)
        budget_hit = stop is not None
    if agent is not None and agent.exhausted:
        budget_hit = True

    # 6. Assemble, render, record pending ledger entries.
    sections: dict[Category, list[SourceResult]] = {}
    if not only or "news" in only:
        sections["news"] = []
    if not only or "podcasts" in only:
        sections["podcast"] = []
    if not only or "articles" in only:
        sections["article"] = []
    if not only or "forums" in only:
        sections["forum"] = []
    for task, res in results:
        sections.setdefault(task.category, []).append(res)
    if feature_results:
        sections["feature"] = feature_results

    for rs in sections.values():
        for r in rs:
            for it in r.items:
                ledger.mark(it.id, it.category, it.title, today)
                if isinstance(it, Feature):
                    loc = next((f.location for f in cfg.features if f.name == r.name), "")
                    ledger.mark_feature(feature_key(it.place_name, loc), today)

    briefing = Briefing(
        date=today.isoformat(),
        generated_at=now,
        timezone=settings.timezone,
        model=settings.model,
        cost_usd=round(agent.usage.cost_usd, 4) if agent else 0.0,
        budget_exhausted=budget_hit,
        ai_enabled=agent is not None,
        sections=sections,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"briefing-{today.isoformat()}.md"
    json_path = out_dir / f"briefing-{today.isoformat()}.json"
    pending_path = out_dir / PENDING_FILE
    md_path.write_text(render_markdown(briefing), encoding="utf-8")
    json_path.write_text(briefing.model_dump_json(indent=2), encoding="utf-8")
    ledger.write_pending(pending_path)

    attempted = [r for rs in sections.values() for r in rs if r.status != "skipped"]
    all_failed = bool(attempted) and all(r.status == "error" for r in attempted)
    return RunOutput(briefing, md_path, json_path, pending_path, all_failed)
