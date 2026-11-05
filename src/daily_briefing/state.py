"""Dedup ledger with GitHub Gist (CI) and local-file (dev) backends."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Protocol

import httpx

from .util import make_client

log = logging.getLogger(__name__)

GIST_FILENAME = "seen.json"
LOCAL_PATH = Path(".state/seen.json")


def empty_ledger() -> dict:
    return {"version": 1, "items": {}, "features": {}, "feeds": {}}


def feature_key(place_name: str, location: str) -> str:
    def norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

    return f"{norm(place_name)}|{norm(location.split(',')[0])}"


class Ledger:
    def __init__(self, data: dict | None = None):
        data = data or empty_ledger()
        self.data = {**empty_ledger(), **data}
        # Changes made during this run, written to the pending file.
        self.pending = {"items": {}, "features": {}, "feeds": {}}

    # --- queries
    def seen(self, item_id: str) -> bool:
        return item_id in self.data["items"] or item_id in self.pending["items"]

    def feature_seen(self, key: str) -> bool:
        return key in self.data["features"] or key in self.pending["features"]

    def featured_names(self) -> list[str]:
        return [k.split("|")[0] for k in [*self.data["features"], *self.pending["features"]]]

    def cached_feed(self, url: str) -> str | None:
        return self.pending["feeds"].get(url) or self.data["feeds"].get(url)

    # --- mutations (recorded as pending)
    def mark(self, item_id: str, category: str, title: str, today: date) -> None:
        self.pending["items"][item_id] = {
            "first_seen": today.isoformat(),
            "category": category,
            "title": title[:200],
        }

    def mark_feature(self, key: str, today: date) -> None:
        self.pending["features"][key] = today.isoformat()

    def cache_feed(self, url: str, feed_url: str) -> None:
        if self.data["feeds"].get(url) != feed_url:
            self.pending["feeds"][url] = feed_url

    # --- persistence helpers
    def write_pending(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.pending, indent=2, ensure_ascii=False), encoding="utf-8")


def merge_pending(data: dict, pending: dict, today: date, retention_days: int) -> dict:
    """Merge pending changes into a ledger and prune old item entries (features are kept forever)."""
    merged = {**empty_ledger(), **data}
    merged["items"] = {**merged["items"], **pending.get("items", {})}
    merged["features"] = {**merged["features"], **pending.get("features", {})}
    merged["feeds"] = {**merged["feeds"], **pending.get("feeds", {})}
    cutoff = (today - timedelta(days=retention_days)).isoformat()
    merged["items"] = {k: v for k, v in merged["items"].items() if v.get("first_seen", "9999") >= cutoff}
    return merged


class Backend(Protocol):
    name: str

    def load(self) -> dict: ...
    def save(self, data: dict) -> None: ...


class LocalBackend:
    name = "local"

    def __init__(self, path: Path = LOCAL_PATH):
        self.path = path

    def load(self) -> dict:
        if not self.path.exists():
            return empty_ledger()
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class GistBackend:
    name = "gist"
    API = "https://api.github.com/gists/{id}"

    def __init__(self, gist_id: str, token: str, client: httpx.Client | None = None):
        self.gist_id = gist_id
        self.client = client or make_client()
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def load(self) -> dict:
        resp = self.client.get(self.API.format(id=self.gist_id), headers=self.headers)
        resp.raise_for_status()
        files = resp.json().get("files", {})
        f = files.get(GIST_FILENAME)
        if not f:
            log.warning("Gist has no %s; starting with an empty ledger", GIST_FILENAME)
            return empty_ledger()
        content = f.get("content", "")
        if f.get("truncated"):
            raw = self.client.get(f["raw_url"], headers=self.headers)
            raw.raise_for_status()
            content = raw.text
        if not content.strip():
            return empty_ledger()
        return json.loads(content)

    def save(self, data: dict) -> None:
        body = {"files": {GIST_FILENAME: {"content": json.dumps(data, indent=1, ensure_ascii=False)}}}
        resp = self.client.patch(self.API.format(id=self.gist_id), headers=self.headers, json=body)
        resp.raise_for_status()


def backend_from_env() -> Backend:
    gist_id, token = os.environ.get("BRIEFING_GIST_ID"), os.environ.get("BRIEFING_GIST_TOKEN")
    if gist_id and token:
        return GistBackend(gist_id, token)
    return LocalBackend()
