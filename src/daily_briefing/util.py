"""Shared helpers: HTTP client, URL normalization, ids, dates, text."""

from __future__ import annotations

import calendar
import hashlib
import html
import re
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

USER_AGENT = "Mozilla/5.0 (compatible; daily-briefing/0.1; +https://github.com/jlawcordova/daily-briefing)"
TIMEOUT = 20.0
RETRIES = 2

_TRACKING_PARAMS = re.compile(r"^(utm_.*|at_.*|ref|ref_src|fbclid|gclid|mc_cid|mc_eid|smid|cmpid)$", re.I)


def make_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        timeout=TIMEOUT,
        follow_redirects=True,
        transport=transport,
    )


def http_get(client: httpx.Client, url: str, **kwargs) -> httpx.Response:
    """GET with simple exponential backoff on network errors and 5xx/429."""
    last_exc: Exception | None = None
    for attempt in range(RETRIES + 1):
        try:
            resp = client.get(url, **kwargs)
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < RETRIES:
                time.sleep(1.5 * (2**attempt))
                continue
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError:
            raise
        except httpx.HTTPError as e:
            last_exc = e
            if attempt < RETRIES:
                time.sleep(1.5 * (2**attempt))
    assert last_exc is not None
    raise last_exc


def _kept_params(query: str) -> list[tuple[str, str]]:
    return [(k, v) for k, v in parse_qsl(query, keep_blank_values=True) if not _TRACKING_PARAMS.match(k)]


def normalize_url(url: str) -> str:
    """Canonical form for dedup: https, lowercase host, no tracking params/fragment/trailing slash."""
    url = url.strip()
    parts = urlsplit(url)
    scheme = "https" if parts.scheme in ("http", "https", "") else parts.scheme
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parts.path.rstrip("/") or ""
    query = urlencode(sorted(_kept_params(parts.query)))
    return urlunsplit((scheme, host, path, query, ""))


def clean_url(url: str) -> str:
    """Strip tracking params and fragments for display, keeping host and path as-is."""
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(_kept_params(parts.query)), ""))


def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def url_id(category: str, url: str) -> str:
    return f"{category}:{sha1(normalize_url(url))[:16]}"


def fallback_id(category: str, source_name: str, title: str, published: datetime | None) -> str:
    stamp = published.date().isoformat() if published else ""
    return f"{category}:{sha1(f'{source_name}|{title}|{stamp}')[:16]}"


def domain_of(url: str) -> str | None:
    host = urlsplit(url).netloc.lower()
    return host[4:] if host.startswith("www.") else (host or None)


def same_site(url: str, base: str) -> bool:
    """True if url's host equals base's host or is a subdomain of it."""
    a, b = domain_of(url), domain_of(base)
    return bool(a and b and (a == b or a.endswith("." + b)))


def struct_to_dt(st: time.struct_time | None) -> datetime | None:
    """feedparser *_parsed values are UTC struct_time."""
    if not st:
        return None
    try:
        return datetime.fromtimestamp(calendar.timegm(st), tz=UTC)
    except (OverflowError, ValueError):
        return None


def parse_date(value: str | None) -> datetime | None:
    """Parse ISO-8601 or RFC-2822 dates; returns aware UTC datetime or None."""
    if not value:
        return None
    value = value.strip()
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t\r\f\v]+")


def strip_html(text: str | None, limit: int | None = None) -> str | None:
    if not text:
        return None
    text = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>", "\n", text)
    text = html.unescape(_TAG_RE.sub("", text))
    text = "\n".join(_WS_RE.sub(" ", line).strip() for line in text.splitlines())
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if limit and len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "…"
    return text or None


def keyword_match(text: str, keywords: list[str]) -> bool:
    """Case-insensitive whole-word match for any keyword."""
    return any(re.search(rf"(?<!\w){re.escape(k)}(?!\w)", text, re.I) for k in keywords)


def parse_duration(value: str | int | None) -> int | None:
    """itunes:duration -> seconds. Accepts 'SS', 'MM:SS', 'HH:MM:SS'."""
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    try:
        parts = [int(float(p)) for p in str(value).strip().split(":")]
    except ValueError:
        return None
    secs = 0
    for p in parts:
        secs = secs * 60 + p
    return secs or None


def format_duration(seconds: int | None) -> str | None:
    if not seconds:
        return None
    h, rem = divmod(seconds, 3600)
    m = rem // 60
    return f"{h}h {m:02d}m" if h else f"{m}m"
