from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from daily_briefing.config import BriefingConfig, Window, load_config

ROOT = Path(__file__).parent.parent


def test_repo_config_is_valid():
    cfg = load_config(ROOT / "config" / "briefing.yaml")
    assert cfg.settings.timezone == "Asia/Manila"
    assert {p.name for p in cfg.podcasts} == {
        "Syntax – Tasty Treats for Web Developers",
        "Soft Skills Engineering",
    }
    assert cfg.features[0].location.startswith("Davao City")


def test_unknown_keys_rejected():
    with pytest.raises(ValidationError):
        BriefingConfig.model_validate({"news": [{"name": "x", "url": "https://a.b", "bogus": 1}]})


def test_duplicate_names_rejected():
    with pytest.raises(ValidationError, match="duplicate"):
        BriefingConfig.model_validate(
            {"news": [{"name": "A", "url": "https://a.b"}], "articles": [{"name": "A", "url": "https://c.d"}]}
        )


def test_bad_timezone_rejected():
    with pytest.raises(ValidationError, match="timezone"):
        BriefingConfig.model_validate({"settings": {"timezone": "Mars/Base"}})


def test_window_kinds_exclusive():
    with pytest.raises(ValidationError):
        Window(lookback_days=3, since="2025-01-01")


def test_window_bounds_absolute_and_relative():
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("Asia/Manila")
    now = datetime(2025, 11, 5, 2, 0, tzinfo=UTC)
    start, end = Window(since="2025-11-01", until="2025-11-03").bounds(now, tz, 2)
    assert start.isoformat().startswith("2025-11-01T00:00") and end.date().isoformat() == "2025-11-03"
    start, end = Window(lookback_days=7).bounds(now, tz, 2)
    assert (end - start).days == 7
    start, _ = Window().bounds(now, tz, 2)
    assert (now - start).days == 2
