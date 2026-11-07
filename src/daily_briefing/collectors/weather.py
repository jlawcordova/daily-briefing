"""Today's weather from MET Norway's Locationforecast API, the forecast behind yr.no.

Deterministic, no AI. The hourly symbols are folded into one `kind` for the day, the vocabulary the
Daily Brief page draws its sky from, plus a short summary by morning, afternoon and evening.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from ..config import WeatherSource
from ..models import Weather
from ..util import http_get
from .base import Context

API = "https://api.met.no/weatherapi/locationforecast/2.0/compact"

# The kinds, driest to wettest. The page has a sky for each.
SKY = ["sun", "fair", "partly", "cloudy", "fog"]
WET = ["drizzle", "showers", "rain", "heavy-rain", "thundershowers", "storm"]
KINDS = SKY + WET

# yr.no's symbol codes (without _day / _night / _polartwilight) -> kind. Sleet and snow never fall in
# the tropics; they map onto the rain of the same strength so an odd place still gets a sky.
SYMBOLS = {
    "clearsky": "sun",
    "fair": "fair",
    "partlycloudy": "partly",
    "cloudy": "cloudy",
    "fog": "fog",
    "lightrain": "drizzle",
    "lightsleet": "drizzle",
    "lightsnow": "drizzle",
    "rain": "rain",
    "sleet": "rain",
    "snow": "rain",
    "heavyrain": "heavy-rain",
    "heavysleet": "heavy-rain",
    "heavysnow": "heavy-rain",
    "lightrainshowers": "showers",
    "rainshowers": "showers",
    "lightsleetshowers": "showers",
    "sleetshowers": "showers",
    "lightsnowshowers": "showers",
    "snowshowers": "showers",
    "heavyrainshowers": "heavy-rain",
    "heavysleetshowers": "heavy-rain",
    "heavysnowshowers": "heavy-rain",
}
THUNDER_SHOWERS = "showersandthunder"
THUNDER = "andthunder"

# How each kind reads in the summary: an adjective before the period, or a noun before "in the".
ADJ = {"sun": "clear", "fair": "mostly sunny", "partly": "partly cloudy", "cloudy": "cloudy", "fog": "foggy"}
NOUN = {
    "drizzle": "light rain",
    "showers": "showers",
    "rain": "rain",
    "heavy-rain": "heavy rain",
    "thundershowers": "thundery showers",
    "storm": "thunderstorms",
}
PERIODS = [("morning", 6, 12), ("afternoon", 12, 18), ("evening", 18, 24)]
DAYTIME = (6, 18)


def kind_of(symbol: str) -> str:
    base = symbol.split("_", 1)[0]
    if base.endswith(THUNDER_SHOWERS):
        return "thundershowers"
    if base.endswith(THUNDER):
        return "storm"
    return SYMBOLS.get(base, "cloudy")


def _sky(kinds: list[str]) -> str:
    """The most common dry kind; a tie goes to the cloudier one."""
    counts = Counter(k for k in kinds if k in SKY)
    if not counts:
        return "cloudy"
    return max(counts, key=lambda k: (counts[k], SKY.index(k)))


def day_kind(kinds: list[str]) -> str:
    """One kind for a run of hourly kinds (the daytime hours)."""
    wet = [k for k in kinds if k in WET]
    if not wet:
        return _sky(kinds)
    c = Counter(wet)
    thunder = c["storm"] + c["thundershowers"]
    if len(wet) * 2 >= len(kinds):  # wet half the day or more: it rains, not just showers
        if thunder >= 2:
            return "storm"
        if c["heavy-rain"] >= 3:
            return "heavy-rain"
        if c["drizzle"] * 2 > len(wet):
            return "drizzle"
        return "rain"
    if thunder:
        return "thundershowers"
    if c["heavy-rain"] >= 2:
        return "heavy-rain"
    if c["drizzle"] == len(wet):
        return "drizzle"
    return "showers"


def period_kind(kinds: list[str]) -> str:
    wet = [k for k in kinds if k in WET]
    if wet:
        return max(wet, key=WET.index)
    return _sky(kinds)


def summarize(by_period: list[tuple[str, str]]) -> str:
    """[("morning", "sun"), ("afternoon", "showers"), ...] -> "Clear morning, showers in the afternoon"."""
    groups: list[tuple[str, list[str]]] = []
    for period, kind in by_period:
        if groups and groups[-1][0] == kind:
            groups[-1][1].append(period)
        else:
            groups.append((kind, [period]))
    parts = []
    for kind, periods in groups:
        when = " and ".join(periods)
        if len(groups) == 1 and len(periods) == len(PERIODS):
            parts.append(f"{ADJ[kind]} all day" if kind in ADJ else f"{NOUN[kind]} all day")
        elif kind in ADJ:
            parts.append(f"{ADJ[kind]} {when}")
        else:
            parts.append(f"{NOUN[kind]} in the {when}")
    text = ", ".join(parts)
    return text[:1].upper() + text[1:]


def collect_weather(ctx: Context, source: WeatherSource) -> Weather | None:
    """Today's weather at the source's place, or None when the forecast has no hours left today."""
    data = http_get(ctx.client, API, params={"lat": f"{source.lat:.2f}", "lon": f"{source.lon:.2f}"}).json()
    tz, today = ctx.settings.tz, ctx.today
    hours: list[tuple[int, float | None, str | None, float]] = []  # (local hour, temp, kind, rain mm)
    for step in data.get("properties", {}).get("timeseries", []):
        at = datetime.fromisoformat(step["time"].replace("Z", "+00:00")).astimezone(tz)
        if at.date() != today:
            continue
        d = step.get("data", {})
        temp = d.get("instant", {}).get("details", {}).get("air_temperature")
        nxt = d.get("next_1_hours") or d.get("next_6_hours") or {}
        sym = nxt.get("summary", {}).get("symbol_code")
        rain = nxt.get("details", {}).get("precipitation_amount", 0.0) if "next_1_hours" in d else 0.0
        hours.append((at.hour, temp, kind_of(sym) if sym else None, float(rain or 0.0)))
    temps = [t for _, t, _, _ in hours if t is not None]
    if not temps:
        return None

    def kinds_in(lo: int, hi: int) -> list[str]:
        return [k for h, _, k, _ in hours if lo <= h < hi and k]

    day = kinds_in(*DAYTIME) or [k for _, _, k, _ in hours if k]
    periods = [(name, period_kind(ks)) for name, lo, hi in PERIODS if (ks := kinds_in(lo, hi))]
    return Weather(
        place=source.place,
        date=today.isoformat(),
        kind=day_kind(day) if day else "cloudy",
        high=round(max(temps)),
        low=round(min(temps)),
        precipitation_mm=round(sum(r for _, _, _, r in hours), 1),
        summary=summarize(periods) if periods else "",
        url=str(source.link) if source.link else None,
    )
