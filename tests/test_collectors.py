from daily_briefing.collectors.hackernews import collect_hackernews
from daily_briefing.collectors.podcast import collect_podcast
from daily_briefing.collectors.rss import collect_rss
from daily_briefing.config import ArticleSource, ForumSource, NewsSource, PodcastSource

from .conftest import fixture

XML = "application/rss+xml"


def test_rss_window_and_cleaning(ctx_factory):
    ctx = ctx_factory({"https://feeds.example.com/news.xml": (200, fixture("news.xml"), XML)})
    src = NewsSource(name="Ex", url="https://feeds.example.com/news.xml")  # default 2-day window
    items = collect_rss(ctx, src, "news")
    titles = [i.title for i in items]
    assert titles == ["Fresh story", "AI breakthrough announced"]
    fresh = items[0]
    assert fresh.url == "https://www.example.com/news/fresh"
    assert fresh.source_description == "Something happened today."
    assert fresh.image_url == "https://img.example.com/fresh.jpg"
    assert fresh.id.startswith("news:")


def test_rss_keyword_filters(ctx_factory):
    ctx = ctx_factory({"https://feeds.example.com/news.xml": (200, fixture("news.xml"), XML)})
    src = ArticleSource(name="Ex", url="https://feeds.example.com/news.xml", lookback_days=10, include_keywords=["LLM"])
    assert [i.title for i in collect_rss(ctx, src, "article")] == ["AI breakthrough announced"]
    src = ArticleSource(name="Ex", url="https://feeds.example.com/news.xml", lookback_days=10, exclude_keywords=["LLM"])
    assert "AI breakthrough announced" not in [i.title for i in collect_rss(ctx, src, "article")]


def test_podcast_website_discovery_and_metadata(ctx_factory):
    ctx = ctx_factory(
        {
            "https://pod.example.com/": (200, fixture("site.html"), "text/html"),
            "https://pod.example.com/feed.xml": (200, fixture("podcast.xml"), XML),
        }
    )
    src = PodcastSource(name="Pod", url="https://pod.example.com/", hosts=["Wes Bos"], window={"lookback_days": 7})
    show, eps = collect_podcast(ctx, src)
    assert show.feed_url == "https://pod.example.com/feed.xml"
    assert len(eps) == 1
    ep = eps[0]
    assert ep.id == "podcast:ep-101"
    assert ep.duration_seconds == 4350
    assert (ep.season, ep.episode_number) == (3, 101) and not ep.explicit
    assert ep.audio_url == "https://cdn.example.com/101.mp3"
    assert "We talk about CSS." in ep.source_description
    assert ep.hosts == ["Wes Bos"]
    # Resolved feed is cached for next time.
    assert ctx.ledger.pending["feeds"]["https://pod.example.com/"] == "https://pod.example.com/feed.xml"


def test_podcast_apple_url_uses_itunes_lookup(ctx_factory):
    ctx = ctx_factory(
        {
            "https://itunes.apple.com/lookup": (
                200,
                {
                    "results": [
                        {
                            "feedUrl": "https://pod.example.com/feed.xml",
                            "collectionViewUrl": "https://podcasts.apple.com/us/podcast/x/id123",
                            "primaryGenreName": "Technology",
                        }
                    ]
                },
                "application/json",
            ),
            "https://pod.example.com/feed.xml": (200, fixture("podcast.xml"), XML),
        }
    )
    src = PodcastSource(name="Pod", url="https://podcasts.apple.com/us/podcast/x/id123", window={"since": "2025-08-01"})
    show, eps = collect_podcast(ctx, src)
    assert show.genre == "Technology"
    assert [e.id for e in eps] == ["podcast:ep-101", "podcast:ep-90"]
    assert eps[0].apple_url == "https://podcasts.apple.com/us/podcast/x/id123"


def test_hackernews_filters(ctx_factory):
    api = "https://hacker-news.firebaseio.com/v0"
    routes = {
        f"{api}/topstories.json": (200, [1, 2, 3, 4], "application/json"),
        f"{api}/item/1.json": (
            200,
            {
                "id": 1,
                "type": "story",
                "title": "Claude ships a thing",
                "score": 300,
                "descendants": 120,
                "by": "alice",
                "time": 1762300000,
                "url": "https://www.anthropic.com/news/x",
            },
            "application/json",
        ),
        f"{api}/item/2.json": (
            200,
            {
                "id": 2,
                "type": "story",
                "title": "Gardening tips",
                "score": 500,
                "descendants": 10,
                "by": "bob",
                "time": 1762300000,
            },
            "application/json",
        ),
        f"{api}/item/3.json": (200, {"id": 3, "type": "story", "title": "AI low", "score": 5}, "application/json"),
        f"{api}/item/4.json": (200, {"id": 4, "type": "job", "title": "AI job", "score": 999}, "application/json"),
    }
    ctx = ctx_factory(routes)
    posts = collect_hackernews(ctx, ForumSource(name="HN", min_points=100))
    assert [p.id for p in posts] == ["hn:1", "hn:2"]
    assert posts[0].domain == "anthropic.com"
    assert posts[1].url == "https://news.ycombinator.com/item?id=2"
    posts = collect_hackernews(ctx, ForumSource(name="HN", keywords=["Claude", "AI"], min_points=10))
    assert [p.id for p in posts] == ["hn:1"]
