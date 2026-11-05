import json
from datetime import date

import httpx

from daily_briefing.state import GistBackend, Ledger, LocalBackend, feature_key, merge_pending


def test_ledger_pending_and_seen():
    led = Ledger({"version": 1, "items": {"a": {"first_seen": "2025-11-01"}}, "features": {}, "feeds": {}})
    assert led.seen("a") and not led.seen("b")
    led.mark("b", "news", "B", date(2025, 11, 5))
    assert led.seen("b")
    assert "b" in led.pending["items"] and "a" not in led.pending["items"]


def test_merge_prunes_items_but_keeps_features():
    data = {
        "items": {"old": {"first_seen": "2025-01-01"}, "recent": {"first_seen": "2025-10-30"}},
        "features": {"ancient cafe|davao city": "2024-01-01"},
        "feeds": {},
    }
    pending = {"items": {"new": {"first_seen": "2025-11-05"}}, "features": {"x|davao city": "2025-11-05"}}
    merged = merge_pending(data, pending, date(2025, 11, 5), retention_days=120)
    assert set(merged["items"]) == {"recent", "new"}
    assert set(merged["features"]) == {"ancient cafe|davao city", "x|davao city"}


def test_feature_key_normalizes():
    assert feature_key("Café  Demitasse!", "Davao City, Philippines") == "caf demitasse|davao city"
    assert feature_key("CAFÉ DEMITASSE", "davao city") == feature_key("Café Demitasse", "Davao City, PH")


def test_local_backend_roundtrip(tmp_path):
    b = LocalBackend(tmp_path / "s" / "seen.json")
    assert b.load()["items"] == {}
    b.save({"version": 1, "items": {"x": {}}, "features": {}, "feeds": {}})
    assert "x" in b.load()["items"]


def test_gist_backend_load_and_save():
    saved = {}

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.headers["Authorization"] == "Bearer tok"
        if req.method == "GET":
            content = json.dumps({"version": 1, "items": {"k": {}}, "features": {}, "feeds": {}})
            return httpx.Response(200, json={"files": {"seen.json": {"content": content, "truncated": False}}})
        saved.update(json.loads(req.content))
        return httpx.Response(200, json={})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    g = GistBackend("gid", "tok", client=client)
    assert "k" in g.load()["items"]
    g.save({"version": 1, "items": {}, "features": {}, "feeds": {}})
    assert "seen.json" in saved["files"]


def test_gist_backend_missing_file_is_empty():
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"files": {}})))
    assert GistBackend("gid", "tok", client=client).load()["items"] == {}
