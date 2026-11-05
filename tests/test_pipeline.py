import json

from daily_briefing.agent.client import Agent
from daily_briefing.config import BriefingConfig
from daily_briefing.pipeline import run_briefing
from daily_briefing.state import Ledger, merge_pending

from .conftest import NOW, FakeAnthropic, echo_summaries, fixture, mock_client, response, tool_use

XML = "application/rss+xml"
API = "https://hacker-news.firebaseio.com/v0"

ROUTES = {
    "https://feeds.example.com/news.xml": (200, fixture("news.xml"), XML),
    "https://pod.example.com/": (200, fixture("site.html"), "text/html"),
    "https://pod.example.com/feed.xml": (200, fixture("podcast.xml"), XML),
    f"{API}/topstories.json": (200, [1], "application/json"),
    f"{API}/item/1.json": (
        200,
        {
            "id": 1,
            "type": "story",
            "title": "Show HN: thing",
            "score": 200,
            "descendants": 50,
            "by": "a",
            "time": 1762300000,
        },
        "application/json",
    ),
}

CFG = BriefingConfig.model_validate(
    {
        "news": [{"name": "Example News", "url": "https://feeds.example.com/news.xml"}],
        "podcasts": [
            {"name": "Pod", "url": "https://pod.example.com/", "hosts": ["Wes Bos"], "window": {"lookback_days": 7}}
        ],
        "articles": [{"name": "Broken Blog", "url": "https://broken.example.com/rss.xml"}],
        "forums": [{"name": "HN", "type": "hackernews", "fetch_body": False}],
        "features": [{"name": "Davao Pick", "location": "Davao City, Philippines"}],
    }
)


def responder(kwargs):
    tool_names = {t["name"] for t in kwargs["tools"]}
    if "submit_feature" in tool_names:
        place = {
            "place_name": "Bean There",
            "description": "Cozy café.",
            "why_featured": "Great pour-overs.",
            "must_try": ["Pour-over"],
            "sources": [{"url": "https://blog.example.com/bean", "title": "Bean There review", "date": "2025-09-01"}],
        }
        return response([tool_use("submit_feature", {"places": [place]})], searches=2)
    return echo_summaries(kwargs)


def test_full_run_renders_and_dedups(tmp_path):
    agent = Agent(client=FakeAnthropic(responder), model="claude-sonnet-4-5", max_usd=5)
    ledger = Ledger()
    out = run_briefing(CFG, ledger, tmp_path, agent=agent, client=mock_client(ROUTES), now=NOW)

    md = out.markdown_path.read_text()
    assert out.markdown_path.name == "briefing-2025-11-05.md"
    assert "# Daily Briefing — Wednesday, 5 November 2025" in md
    assert "[Fresh story](https://www.example.com/news/fresh)" in md
    assert "Summary of Fresh story" in md
    assert "101: Talking CSS with Jane Doe" in md and "| Duration | 1h 12m |" in md
    assert "| Guests | Jane Doe |" in md and "| Hosts | Wes Bos |" in md
    assert "Show notes (from the episode)" in md
    assert "▲ 200" in md
    assert "### Bean There" in md and "Bean There review (2025-09-01)" in md
    assert "_Could not fetch this source" in md  # broken blog reported, run continues
    assert "| Broken Blog | article | ❌ |" in md
    assert not out.all_failed

    data = json.loads(out.json_path.read_text())
    assert data["sections"]["podcast"][0]["items"][0]["duration_seconds"] == 4350

    pending = json.loads(out.pending_path.read_text())
    assert "podcast:ep-101" in pending["items"] and "hn:1" in pending["items"]
    assert "bean there|davao city" in pending["features"]

    # Second run with the merged ledger shows nothing already seen.
    merged = merge_pending({}, pending, NOW.date(), 120)
    agent2 = Agent(client=FakeAnthropic(responder), model="claude-sonnet-4-5", max_usd=5)
    out2 = run_briefing(CFG, Ledger(merged), tmp_path / "2", agent=agent2, client=mock_client(ROUTES), now=NOW)
    md2 = out2.markdown_path.read_text()
    assert "Fresh story" not in md2 and "101: Talking CSS" not in md2
    assert md2.count("_Nothing new since the last briefing._") >= 3
    # The feature agent is told not to repeat the earlier pick.
    feature_call = next(c for c in agent2.client.calls if any(t["name"] == "submit_feature" for t in c["tools"]))
    assert "bean there" in feature_call["system"][0]["text"]


def test_no_ai_run_skips_agent_sources(tmp_path):
    out = run_briefing(CFG, Ledger(), tmp_path, agent=None, client=mock_client(ROUTES), now=NOW)
    md = out.markdown_path.read_text()
    assert "AI enrichment was disabled" in md
    assert "_No feature today: needs AI agent (disabled)_" in md
    assert "AI summary" not in md


def test_all_failed_flag(tmp_path):
    cfg = BriefingConfig.model_validate({"news": [{"name": "Down", "url": "https://down.example.com/rss"}]})
    out = run_briefing(cfg, Ledger(), tmp_path, agent=None, client=mock_client({}), now=NOW)
    assert out.all_failed
