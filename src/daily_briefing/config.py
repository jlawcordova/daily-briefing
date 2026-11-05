"""Configuration models and loader for config/briefing.yaml."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Budget(_Strict):
    max_usd_per_run: float = Field(1.00, ge=0)


class ModelPricing(_Strict):
    """USD per million tokens. Overrides the built-in table for unknown/new models."""

    input_per_mtok: float = Field(ge=0)
    output_per_mtok: float = Field(ge=0)
    cache_read_multiplier: float = Field(0.10, ge=0)


class Settings(_Strict):
    timezone: str = "Asia/Manila"
    model: str = "claude-sonnet-5-5"
    # Sonnet 5.5 thinks by default. "between_tools" skips thinking before the first tool call (cheaper, faster).
    # Use "adaptive" for more thinking, or "omit" for older models that don't accept these modes.
    thinking: Literal["between_tools", "adaptive", "omit"] = "between_tools"
    effort: Literal["low", "medium", "high"] | None = "medium"  # None = don't send output_config.effort
    pricing: ModelPricing | None = None
    max_items_per_source: int = Field(10, ge=1, le=100)
    default_lookback_days: int = Field(2, ge=1)
    summary_length: Literal["short", "medium"] = "short"
    dedup_retention_days: int = Field(120, ge=7)
    budget: Budget = Budget()

    @field_validator("timezone")
    @classmethod
    def _valid_tz(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError) as e:
            raise ValueError(f"unknown timezone {v!r}") from e
        return v

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


class Window(_Strict):
    lookback_days: int | None = Field(None, ge=1)
    since: date | None = None
    until: date | None = None

    @model_validator(mode="after")
    def _one_kind(self) -> Window:
        if self.lookback_days and (self.since or self.until):
            raise ValueError("use either lookback_days or since/until, not both")
        if self.since and self.until and self.since > self.until:
            raise ValueError("since must be on or before until")
        return self

    def bounds(self, now: datetime, tz: ZoneInfo, default_days: int) -> tuple[datetime, datetime]:
        """Return an inclusive [start, end] window in aware datetimes."""
        if self.since or self.until:
            start = datetime.combine(self.since, time.min, tz) if self.since else datetime(1970, 1, 1, tzinfo=tz)
            end = datetime.combine(self.until, time.max, tz) if self.until else now
            return start, end
        days = self.lookback_days or default_days
        return now - timedelta(days=days), now


class _SourceBase(_Strict):
    name: str = Field(min_length=1)
    enabled: bool = True
    max_items: int | None = Field(None, ge=1, le=100)


class NewsSource(_SourceBase):
    type: Literal["rss", "web"] = "rss"
    url: HttpUrl
    lookback_days: int | None = Field(None, ge=1)
    fetch_body: bool = False


class PodcastSource(_SourceBase):
    url: HttpUrl
    feed_url: HttpUrl | None = None
    hosts: list[str] = []
    window: Window = Window()


class ArticleSource(_SourceBase):
    type: Literal["rss", "web"] = "rss"
    url: HttpUrl
    lookback_days: int | None = Field(None, ge=1)
    include_keywords: list[str] = []
    exclude_keywords: list[str] = []
    fetch_body: bool = True


class ForumSource(_SourceBase):
    type: Literal["hackernews"] = "hackernews"
    feed: Literal["top", "best", "new", "ask", "show"] = "top"
    min_points: int = Field(0, ge=0)
    min_comments: int = Field(0, ge=0)
    keywords: list[str] = []
    scan_limit: int = Field(100, ge=1, le=500)
    fetch_body: bool = True


class FeatureSource(_SourceBase):
    type: Literal["local_food"] = "local_food"
    location: str
    freshness_days: int = Field(365, ge=1)
    count: int = Field(1, ge=1, le=5)
    criteria: str = ""


class BriefingConfig(_Strict):
    version: Literal[1] = 1
    settings: Settings = Settings()
    news: list[NewsSource] = []
    podcasts: list[PodcastSource] = []
    articles: list[ArticleSource] = []
    forums: list[ForumSource] = []
    features: list[FeatureSource] = []

    @model_validator(mode="after")
    def _unique_names(self) -> BriefingConfig:
        seen: set[str] = set()
        for src in [*self.news, *self.podcasts, *self.articles, *self.forums, *self.features]:
            if src.name in seen:
                raise ValueError(f"duplicate source name: {src.name!r}")
            seen.add(src.name)
        return self


def load_config(path: str | Path) -> BriefingConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return BriefingConfig.model_validate(raw)
