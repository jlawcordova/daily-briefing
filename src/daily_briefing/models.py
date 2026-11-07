"""Data model for collected items and run results."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, SerializeAsAny

Category = Literal["news", "podcast", "article", "forum", "feature", "weather"]


class Item(BaseModel):
    id: str
    category: Category
    source_name: str
    title: str
    url: str
    published_at: datetime | None = None
    author: str | None = None
    source_description: str | None = None
    image_url: str | None = None
    tags: list[str] = []
    # Context for the agent; not rendered verbatim.
    body_excerpt: str | None = None
    reading_time_min: int | None = None
    # Agent-generated
    ai_summary: str | None = None
    ai_why_it_matters: str | None = None
    ai_tags: list[str] = []


class Episode(Item):
    category: Category = "podcast"
    show_name: str
    episode_number: int | None = None
    season: int | None = None
    episode_type: str | None = None
    duration_seconds: int | None = None
    audio_url: str | None = None
    hosts: list[str] = []
    guests: list[str] = []
    explicit: bool | None = None
    apple_url: str | None = None


class Article(Item):
    pass


class ForumPost(Item):
    category: Category = "forum"
    points: int = 0
    comments: int = 0
    comments_url: str
    submitter: str | None = None
    domain: str | None = None


class FeatureSourceRef(BaseModel):
    url: str
    title: str
    date: str | None = None


class Feature(Item):
    category: Category = "feature"
    place_name: str
    address: str | None = None
    neighborhood: str | None = None
    price_range: str | None = None
    hours: str | None = None
    must_try: list[str] = []
    why_featured: str | None = None
    sources: list[FeatureSourceRef] = []
    map_url: str | None = None


class ShowInfo(BaseModel):
    """Podcast show-level metadata (from the feed and/or iTunes)."""

    name: str
    feed_url: str
    website: str | None = None
    apple_url: str | None = None
    artwork_url: str | None = None
    author: str | None = None
    genre: str | None = None


class SourceResult(BaseModel):
    name: str
    category: Category
    status: Literal["ok", "warn", "error", "skipped"] = "ok"
    fetched: int = 0
    new: int = 0
    notes: str = ""
    items: list[SerializeAsAny[Item]] = Field(default_factory=list)
    show: ShowInfo | None = None


WeatherKind = Literal[
    "sun", "fair", "partly", "cloudy", "fog", "drizzle", "showers", "rain", "heavy-rain", "thundershowers", "storm"
]


class Weather(BaseModel):
    """Today's weather at one place: the Daily Brief page draws its sky from `kind`."""

    place: str
    date: str
    kind: WeatherKind
    high: int
    low: int
    precipitation_mm: float = 0.0
    summary: str = ""
    url: str | None = None


class Briefing(BaseModel):
    date: str
    generated_at: datetime
    timezone: str
    model: str
    cost_usd: float = 0.0
    budget_exhausted: bool = False
    ai_enabled: bool = True
    sections: dict[Category, list[SourceResult]]
    weather: Weather | None = None
    weather_report: SourceResult | None = None
