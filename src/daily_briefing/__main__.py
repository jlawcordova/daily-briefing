"""CLI: python -m daily_briefing {run,commit-state,validate}."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from .config import load_config
from .state import Ledger, backend_from_env, merge_pending

log = logging.getLogger("daily_briefing")
SECTION_NAMES = {"news", "podcasts", "articles", "forums", "features"}


def cmd_validate(args) -> int:
    try:
        cfg = load_config(args.config)
    except (ValidationError, OSError, ValueError) as e:
        print(f"Invalid config: {e}", file=sys.stderr)
        return 2
    counts = {k: len(getattr(cfg, k)) for k in sorted(SECTION_NAMES)}
    print(f"OK: {args.config} " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    return 0


def cmd_run(args) -> int:
    from .agent.client import make_agent
    from .pipeline import run_briefing
    from .util import make_client

    try:
        cfg = load_config(args.config)
    except (ValidationError, OSError, ValueError) as e:
        print(f"Invalid config: {e}", file=sys.stderr)
        return 2

    only = None
    if args.only:
        only = {s.strip() for s in args.only.split(",") if s.strip()}
        bad = only - SECTION_NAMES
        if bad:
            print(f"Unknown section(s) in --only: {', '.join(sorted(bad))}", file=sys.stderr)
            return 2

    agent = None
    if not args.no_ai:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            print("ANTHROPIC_API_KEY is not set (use --no-ai to run without Claude).", file=sys.stderr)
            return 2
        s = cfg.settings
        agent = make_agent(key, s.model, s.budget.max_usd_per_run, s.pricing, s.thinking, s.effort)

    backend = backend_from_env()
    ledger = Ledger(backend.load())
    log.info("ledger backend=%s items=%d", backend.name, len(ledger.data["items"]))

    with make_client() as client:
        out = run_briefing(
            cfg,
            ledger,
            Path(args.out),
            agent=agent,
            client=client,
            ignore_seen=args.ignore_seen,
            only=only,
        )
    total = sum(len(r.items) for rs in out.briefing.sections.values() for r in rs)
    print(f"Wrote {out.markdown_path} ({total} new items, est. cost ${out.briefing.cost_usd:.2f})")
    if agent:
        u = agent.usage
        log.info(
            "usage: calls=%d in=%d out=%d cache_r=%d searches=%d",
            u.calls,
            u.input_tokens,
            u.output_tokens,
            u.cache_read_tokens,
            u.web_searches,
        )

    if args.commit and not args.dry_run:
        _commit(out.pending_path, cfg.settings.dedup_retention_days, cfg.settings.tz)
    if out.all_failed:
        print("Every source failed.", file=sys.stderr)
        return 1
    return 0


def _commit(pending_path: Path, retention_days: int, tz) -> None:
    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    backend = backend_from_env()
    data = backend.load()
    today = datetime.now(UTC).astimezone(tz).date()
    merged = merge_pending(data, pending, today, retention_days)
    backend.save(merged)
    print(f"Ledger saved to {backend.name}: +{len(pending.get('items', {}))} items, {len(merged['items'])} total")


def cmd_commit_state(args) -> int:
    path = Path(args.pending)
    if not path.exists():
        print(f"No pending file at {path}; nothing to commit.", file=sys.stderr)
        return 1
    cfg = load_config(args.config)
    _commit(path, cfg.settings.dedup_retention_days, cfg.settings.tz)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="daily_briefing", description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="cmd")

    run = sub.add_parser("run", help="generate a briefing")
    run.add_argument("--config", default="config/briefing.yaml")
    run.add_argument("--out", default="output")
    run.add_argument("--dry-run", action="store_true", help="never write the ledger")
    run.add_argument("--commit", action="store_true", help="save the ledger right after rendering (local use)")
    run.add_argument("--ignore-seen", action="store_true", help="include items already in the ledger")
    run.add_argument("--only", help="comma list: news,podcasts,articles,forums,features")
    run.add_argument("--no-ai", action="store_true", help="skip Claude (no summaries, web sources, feature)")
    run.set_defaults(func=cmd_run)

    cs = sub.add_parser("commit-state", help="merge pending ledger entries into the store")
    cs.add_argument("--config", default="config/briefing.yaml")
    cs.add_argument("--pending", default="output/.pending-seen.json")
    cs.set_defaults(func=cmd_commit_state)

    val = sub.add_parser("validate", help="validate the config file")
    val.add_argument("--config", default="config/briefing.yaml")
    val.set_defaults(func=cmd_validate)

    args = parser.parse_args(argv)
    if not args.cmd:  # default to `run`
        args = parser.parse_args(["run", *(argv if argv is not None else sys.argv[1:])])
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    for noisy in ("httpx", "httpcore", "trafilatura"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
