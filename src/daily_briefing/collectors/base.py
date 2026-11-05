"""Shared collector context."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

import httpx

from ..config import Settings
from ..state import Ledger

if TYPE_CHECKING:
    from ..agent.client import Agent


@dataclass
class Context:
    client: httpx.Client
    settings: Settings
    ledger: Ledger
    now: datetime
    agent: Agent | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def today(self):
        return self.now.astimezone(self.settings.tz).date()


def in_window(dt: datetime | None, start: datetime, end: datetime) -> bool:
    """Items without a date are allowed through (dedup protects against repeats)."""
    return dt is None or start <= dt <= end
