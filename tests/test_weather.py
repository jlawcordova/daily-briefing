from datetime import UTC, datetime, timedelta

import pytest

from daily_briefing.collectors.weather import API, KINDS, collect_weather, day_kind, kind_of, summarize
from daily_briefing.config import BriefingConfig, WeatherSource
from daily_briefing.models import WeatherKind
from daily_briefing.pipeline import run_briefing
from daily_briefing.publish import entry_from_briefing
from daily_briefing.state import Ledger

from .conftest import NOW, mock_client

SOURCE = WeatherSource(place="Davao City", lat=7.07, lon=125.61, link="https://www.yr.no/en/forecast/x")
DAY_START = datetime(2025, 11, 4, 22, 0, tzinfo=UTC)  # 06:00 on 2025-11-05 in Manila


def forecast(symbols: list[str], temps: list[float] | None = None, rain: float = 0.0) -> dict:
    """A MET Norway `compact` response: one hourly step per symbol from 06:00 Manila."""
    temps = temps or [24 + (i % 8) for i in range(len(symbols))]
    steps = []
    for i, (sym, t) in enumerate(zip(symbols, temps, strict=True)):
        at = DAY_START + timedelta(hours=i)
        steps.append(
            {
                "time": at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "data": {
                    "instant": {"details": {"air_temperature": t}},
                    "next_1_hours": {
                        "summary": {"symbol_code": sym},
                        "details": {"precipitation_amount": rain if "rain" in sym else 0.0},
                    },
                },
            }
        )
    return {"type": "Feature", "properties": {"timeseries": steps}}


def test_kinds_match_the_model():
    assert list(WeatherKind.__args__) == KINDS


@pytest.mark.parametrize(
    ("symbol", "kind"),
    [
        ("clearsky_day", "sun"),
        ("clearsky_night", "sun"),
        ("fair_day", "fair"),
        ("partlycloudy_polartwilight", "partly"),
        ("cloudy", "cloudy"),
        ("fog", "fog"),
        ("lightrain", "drizzle"),
        ("rain", "rain"),
        ("heavyrain", "heavy-rain"),
        ("rainshowers_day", "showers"),
        ("heavyrainshowers_day", "heavy-rain"),
        ("lightrainshowersandthunder_day", "thundershowers"),
        ("rainandthunder", "storm"),
        ("heavyrainandthunder", "storm"),
        ("something_new", "cloudy"),
    ],
)
def test_kind_of_yr_symbols(symbol, kind):
    assert kind_of(symbol) == kind


def test_day_kind():
    assert day_kind(["sun"] * 8 + ["fair"] * 4) == "sun"
    assert day_kind(["partly"] * 6 + ["cloudy"] * 6) == "cloudy"  # tie goes cloudier
    assert day_kind(["sun"] * 10 + ["showers"] * 2) == "showers"
    assert day_kind(["partly"] * 10 + ["thundershowers"] * 2) == "thundershowers"
    assert day_kind(["cloudy"] * 4 + ["rain"] * 8) == "rain"
    assert day_kind(["cloudy"] * 2 + ["heavy-rain"] * 4 + ["rain"] * 6) == "heavy-rain"
    assert day_kind(["cloudy"] * 4 + ["storm"] * 3 + ["rain"] * 5) == "storm"
    assert day_kind(["cloudy"] * 4 + ["drizzle"] * 8) == "drizzle"
    assert day_kind(["fog"] * 7 + ["cloudy"] * 5) == "fog"


def test_summarize():
    assert summarize([("morning", "sun"), ("afternoon", "showers"), ("evening", "showers")]) == (
        "Clear morning, showers in the afternoon and evening"
    )
    assert summarize([("morning", "partly"), ("afternoon", "partly"), ("evening", "partly")]) == (
        "Partly cloudy all day"
    )
    assert summarize([("morning", "rain"), ("afternoon", "rain"), ("evening", "rain")]) == "Rain all day"


def test_collect_weather_folds_the_day(ctx_factory):
    symbols = ["clearsky_day"] * 6 + ["rainshowers_day"] * 2 + ["partlycloudy_day"] * 4 + ["fair_night"] * 6
    ctx = ctx_factory({API: (200, forecast(symbols, rain=1.2), "application/json")})
    w = collect_weather(ctx, SOURCE)
    assert w is not None
    assert w.kind == "showers"
    assert w.date == "2025-11-05"
    assert (w.high, w.low) == (31, 24)
    assert w.precipitation_mm == 2.4
    assert w.summary == "Clear morning, showers in the afternoon, mostly sunny evening"
    assert w.url == "https://www.yr.no/en/forecast/x"


def test_collect_weather_skips_other_days(ctx_factory):
    data = forecast(["cloudy"] * 2)
    for step in data["properties"]["timeseries"]:
        step["time"] = "2025-11-07T00:00:00Z"
    ctx = ctx_factory({API: (200, data, "application/json")})
    assert collect_weather(ctx, SOURCE) is None


CFG = BriefingConfig.model_validate({"weather": {"place": "Davao City", "lat": 7.07, "lon": 125.61}})


def test_weather_in_the_briefing_and_feed(tmp_path):
    symbols = ["rainandthunder"] * 8 + ["cloudy"] * 4
    client = mock_client({API: (200, forecast(symbols), "application/json")})
    out = run_briefing(CFG, Ledger(), tmp_path, agent=None, client=client, now=NOW, only={"weather"})
    md = out.markdown_path.read_text()
    assert "## ⛅ Weather" in md
    assert "**Davao City:** Thunderstorms in the morning and afternoon" in md
    assert "- **Sky:** `storm`" in md
    assert "| Weather | weather | ✅ | 1 | 1 | storm, 31°/24° |" in md
    assert out.briefing.weather is not None and out.briefing.weather.kind == "storm"
    assert '"kind": "storm"' in out.json_path.read_text()
    entry = entry_from_briefing(out.briefing, md)
    assert entry.summary.endswith("Weather: Thunderstorms in the morning and afternoon, 31°/24°C")
    assert not out.all_failed


def test_weather_failure_is_reported(tmp_path):
    client = mock_client({})
    out = run_briefing(CFG, Ledger(), tmp_path, agent=None, client=client, now=NOW, only={"weather"})
    md = out.markdown_path.read_text()
    assert "_No forecast today: HTTPStatusError" in md
    assert "| Weather | weather | ❌ |" in md
    assert out.briefing.weather is None
    assert out.all_failed
