from daily_briefing.collectors.podcast import apple_id, discover_feed_links
from daily_briefing.util import (
    clean_url,
    format_duration,
    keyword_match,
    normalize_url,
    parse_date,
    parse_duration,
    same_site,
    strip_html,
    url_id,
)


def test_normalize_url_strips_tracking_and_variants():
    a = normalize_url("http://WWW.Example.com/a/b/?utm_source=x&id=2&at_medium=RSS#frag")
    b = normalize_url("https://example.com/a/b?id=2")
    assert a == b == "https://example.com/a/b?id=2"
    assert url_id("news", "http://www.example.com/x/") == url_id("news", "https://example.com/x")


def test_clean_url_keeps_host():
    assert clean_url("https://www.bbc.co.uk/news/a?at_medium=RSS&at_campaign=rss") == "https://www.bbc.co.uk/news/a"


def test_parse_duration():
    assert parse_duration("01:12:30") == 4350
    assert parse_duration("45:00") == 2700
    assert parse_duration("2700") == 2700
    assert parse_duration("") is None
    assert parse_duration("abc") is None
    assert format_duration(4350) == "1h 12m"
    assert format_duration(2700) == "45m"


def test_parse_date_formats():
    assert parse_date("2025-11-04").year == 2025
    assert parse_date("Tue, 04 Nov 2025 10:00:00 GMT").hour == 10
    assert parse_date("2025-11-04T10:00:00Z").tzinfo is not None
    assert parse_date("not a date") is None


def test_keyword_match_whole_word():
    assert keyword_match("New AI model released", ["AI"])
    assert not keyword_match("Said the chair", ["AI"])
    assert keyword_match("Using LLMs at work", ["LLMs"])


def test_strip_html():
    assert strip_html("<p>Hello <b>world</b> &amp; co</p>") == "Hello world & co"
    assert strip_html("x" * 50 + " " + "y" * 50, limit=60).endswith("…")


def test_same_site():
    assert same_site("https://blog.example.com/x", "https://example.com")
    assert same_site("https://www.example.com/x", "https://example.com/news")
    assert not same_site("https://evil.com/example.com", "https://example.com")


def test_apple_id():
    assert apple_id("https://podcasts.apple.com/us/podcast/syntax/id1253186678") == "1253186678"
    assert apple_id("https://syntax.fm") is None


def test_discover_feed_links():
    html = '<link rel="alternate" type="application/rss+xml" href="/feed.xml">'
    assert discover_feed_links(html, "https://softskills.audio/") == ["https://softskills.audio/feed.xml"]
