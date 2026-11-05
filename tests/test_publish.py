import json
import xml.etree.ElementTree as ET

from daily_briefing.models import Briefing, Item, SourceResult
from daily_briefing.publish import build_site
from daily_briefing.render.markdown import render_markdown

from .conftest import NOW, mock_client

BASE = "https://me.github.io/daily-briefing"


def write_briefing(out_dir, date="2025-11-05"):
    item = Item(id="a", category="news", source_name="N", title="Big <news>", url="https://x.com/a")
    b = Briefing(
        date=date,
        generated_at=NOW,
        timezone="Asia/Manila",
        model="m",
        sections={"news": [SourceResult(name="N", category="news", items=[item])]},
    )
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"briefing-{date}.md").write_text(render_markdown(b), encoding="utf-8")
    (out_dir / f"briefing-{date}.json").write_text(b.model_dump_json(), encoding="utf-8")


def test_publish_first_run(tmp_path):
    write_briefing(tmp_path / "out")
    site = tmp_path / "site"
    entries = build_site(tmp_path / "out", site, BASE + "/", client=mock_client({}))
    assert [e.date for e in entries] == ["2025-11-05"]
    assert entries[0].summary.startswith("1 new items (1 news)")

    feed = ET.parse(site / "feed.xml").getroot()
    items = feed.findall("channel/item")
    assert len(items) == 1
    assert items[0].findtext("link") == f"{BASE}/briefings/2025-11-05.html"
    content = items[0].findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
    assert "<h1>" in content and "Big &lt;news&gt;" in content
    assert (site / "briefings/2025-11-05.md").read_text() == (site / "latest.md").read_text()
    assert "Big &lt;news&gt;" in (site / "briefings/2025-11-05.html").read_text()
    assert json.loads((site / "index.json").read_text())["latest"] == "2025-11-05"


def test_publish_keeps_history_and_replaces_same_day(tmp_path):
    index = {
        "briefings": [
            {"date": "2025-11-05", "title": "old today", "generated_at": NOW.isoformat(), "summary": "s"},
            {"date": "2025-11-04", "title": "yesterday", "generated_at": NOW.isoformat(), "summary": "s"},
            {"date": "2025-11-03", "title": "gone", "generated_at": NOW.isoformat(), "summary": "s"},
            {"date": "../evil", "title": "x", "generated_at": NOW.isoformat(), "summary": "s"},
        ]
    }
    client = mock_client(
        {
            f"{BASE}/index.json": (200, index, "application/json"),
            f"{BASE}/briefings/2025-11-05.md": (200, "# old today\n", "text/markdown"),
            f"{BASE}/briefings/2025-11-04.md": (200, "# yesterday\n", "text/markdown"),
            # 2025-11-03.md is missing -> dropped
        }
    )
    write_briefing(tmp_path / "out")
    site = tmp_path / "site"
    entries = build_site(tmp_path / "out", site, BASE, client=client)
    assert [e.date for e in entries] == ["2025-11-05", "2025-11-04"]
    assert "Big" in (site / "briefings/2025-11-05.md").read_text()
    assert (site / "briefings/2025-11-04.md").read_text() == "# yesterday\n"
    assert len(ET.parse(site / "feed.xml").getroot().findall("channel/item")) == 2

    entries = build_site(tmp_path / "out", tmp_path / "site2", BASE, keep=1, client=client)
    assert [e.date for e in entries] == ["2025-11-05"]
