from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from daily_briefing.collectors.base import Context
from daily_briefing.config import Settings
from daily_briefing.state import Ledger

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2025, 11, 5, 2, 0, tzinfo=UTC)  # 10:00 Asia/Manila


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def mock_client(routes: dict[str, tuple[int, bytes | str | dict, str]]) -> httpx.Client:
    """routes: url (without query) -> (status, body, content_type)."""

    def handler(request: httpx.Request) -> httpx.Response:
        key = str(request.url.copy_with(query=None))
        if key not in routes:
            return httpx.Response(404, text="not found")
        status, body, ctype = routes[key]
        if isinstance(body, dict | list):
            return httpx.Response(status, json=body)
        content = body.encode() if isinstance(body, str) else body
        return httpx.Response(status, content=content, headers={"content-type": ctype})

    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)


@pytest.fixture
def ctx_factory():
    def make(routes: dict, agent=None, ledger: Ledger | None = None) -> Context:
        return Context(
            client=mock_client(routes),
            settings=Settings(),
            ledger=ledger or Ledger(),
            now=NOW,
            agent=agent,
        )

    return make


# ---------------------------------------------------------------- fake Claude
def _block(**kw):
    return SimpleNamespace(**kw)


def tool_use(name: str, input: dict, id: str = "tu_1"):
    return _block(type="tool_use", name=name, input=input, id=id)


def text(t: str):
    return _block(type="text", text=t)


def response(content: list, stop_reason: str = "tool_use", searches: int = 0):
    usage = SimpleNamespace(
        input_tokens=1000,
        output_tokens=200,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
        server_tool_use=SimpleNamespace(web_search_requests=searches, web_fetch_requests=0),
    )
    return SimpleNamespace(content=content, stop_reason=stop_reason, usage=usage)


class FakeAnthropic:
    """Returns queued responses or computes them from a callable(kwargs)."""

    def __init__(self, responder):
        self.calls: list[dict] = []
        self._responder = responder
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if callable(self._responder):
            return self._responder(kwargs)
        return self._responder.pop(0)


def echo_summaries(kwargs) -> SimpleNamespace:
    """Responder that summarizes every item in the user payload."""
    user = kwargs["messages"][0]["content"]
    items = json.loads(user.split("Items:\n", 1)[1])
    out = [
        {
            "id": it["id"],
            "summary": f"Summary of {it['title']}",
            "why_it_matters": "It matters.",
            "tags": ["Test"],
            "guests": ["Jane Doe", "Wes Bos"],
        }
        for it in items
    ]
    return response([tool_use("submit_summaries", {"items": out})])
