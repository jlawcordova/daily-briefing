"""Readable-text extraction for article context (summaries, reading time)."""

from __future__ import annotations

import logging
import math
import threading
from concurrent.futures import ThreadPoolExecutor

import httpx
import trafilatura

from ..models import Item
from ..util import http_get

log = logging.getLogger(__name__)

SKIP_EXT = (".pdf", ".mp4", ".mp3", ".zip", ".png", ".jpg", ".gif", ".mov")
SKIP_HOSTS = ("youtube.com", "youtu.be", "x.com", "twitter.com")
WPM = 230
MAX_HTML_CHARS = 2_000_000

# lxml (under trafilatura) segfaulted intermittently when pages were parsed from several threads
# at once (Actions run 42432310634, exit 139). Fetching stays concurrent; parsing is serialised.
_PARSE_LOCK = threading.Lock()


def extract_text(client: httpx.Client, url: str) -> str | None:
    lower = url.lower()
    if lower.split("?")[0].endswith(SKIP_EXT) or any(h in lower for h in SKIP_HOSTS):
        return None
    resp = http_get(client, url)
    if "html" not in resp.headers.get("content-type", "html"):
        return None
    with _PARSE_LOCK:
        text = trafilatura.extract(resp.text[:MAX_HTML_CHARS], include_comments=False, include_tables=False)
    return text or None


def enrich_bodies(client: httpx.Client, items: list[Item], excerpt_chars: int = 1500) -> None:
    """Populate body_excerpt and reading_time_min in place; failures are ignored."""

    def work(item: Item) -> None:
        try:
            text = extract_text(client, item.url)
        except Exception as e:  # network errors, paywalls, etc.
            log.debug("body fetch failed for %s: %s", item.url, e)
            return
        if not text:
            return
        item.body_excerpt = text[:excerpt_chars]
        item.reading_time_min = max(1, math.ceil(len(text.split()) / WPM))

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(work, items))
