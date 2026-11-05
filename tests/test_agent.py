import pytest

from daily_briefing.agent.client import Agent, AgentError, BudgetExceeded
from daily_briefing.agent.enrich import enrich_items
from daily_briefing.agent.feature import collect_feature
from daily_briefing.agent.web import collect_web
from daily_briefing.config import ArticleSource, FeatureSource
from daily_briefing.models import Article, Episode
from daily_briefing.state import Ledger, feature_key

from .conftest import FakeAnthropic, echo_summaries, response, text, tool_use


def make_agent(responder, max_usd=5.0):
    return Agent(client=FakeAnthropic(responder), model="claude-sonnet-4-5", max_usd=max_usd)


def test_enrich_fills_fields_and_filters_hosts():
    agent = make_agent(echo_summaries)
    art = Article(id="a1", category="article", source_name="S", title="T", url="https://x")
    ep = Episode(id="p1", source_name="Pod", show_name="Pod", title="E", url="https://y", hosts=["Wes Bos"])
    n, stop = enrich_items(agent, [art, ep], "short")
    assert (n, stop) == (2, None)
    assert art.ai_summary == "Summary of T" and art.ai_tags == ["test"]
    assert ep.guests == ["Jane Doe"]  # host removed
    assert agent.usage.calls == 2  # one batch per category
    assert agent.usage.cost_usd == pytest.approx(2 * (1000 * 3 + 200 * 15) / 1e6)  # sonnet-4-5 rates


def test_enrich_stops_at_budget():
    agent = make_agent(echo_summaries, max_usd=0.0)
    art = Article(id="a1", category="article", source_name="S", title="T", url="https://x")
    n, stop = enrich_items(agent, [art], "short")
    assert n == 0 and "budget" in stop
    assert art.ai_summary is None


def test_run_tools_handles_custom_tools_and_submit():
    calls = []
    queue = [
        response([text("checking"), tool_use("lookup", {"q": "x"}, id="t1")]),
        response([tool_use("submit", {"answer": 42}, id="t2")]),
    ]
    agent = make_agent(queue)
    out = agent.run_tools(
        "sys",
        "user",
        tools=[{"name": "lookup", "description": "d", "input_schema": {"type": "object"}}],
        submit_tool={"name": "submit", "description": "d", "input_schema": {"type": "object"}},
        handlers={"lookup": lambda inp: calls.append(inp) or "result"},
    )
    assert out == {"answer": 42}
    assert calls == [{"q": "x"}]
    second = agent.client.calls[1]["messages"]
    assert second[-1]["content"][0]["type"] == "tool_result"


def test_run_tools_nudges_instead_of_forcing_tool_choice():
    queue = [response([text("done?")], stop_reason="end_turn"), response([tool_use("submit", {"ok": True})])]
    agent = make_agent(queue)
    out = agent.run_tools("s", "u", [], {"name": "submit", "description": "", "input_schema": {}}, max_turns=2)
    assert out == {"ok": True}
    second = agent.client.calls[1]
    assert second["tool_choice"] == {"type": "auto"}  # Sonnet 5.5 rejects forced tool_choice
    assert "out of steps" in second["messages"][-1]["content"][-1]["text"]


def test_requests_use_thinking_effort_and_strict_tools():
    agent = make_agent(echo_summaries)
    enrich_items(agent, [Article(id="a", category="article", source_name="S", title="T", url="https://x")], "short")
    call = agent.client.calls[0]
    assert call["thinking"] == {"type": "between_tools"}
    assert call["output_config"] == {"effort": "medium"}
    tool = call["tools"][0]
    assert tool["strict"] is True
    assert tool["input_schema"]["additionalProperties"] is False
    assert tool["input_schema"]["properties"]["items"]["items"]["additionalProperties"] is False


def test_thinking_omit_for_older_models():
    agent = make_agent(echo_summaries)
    agent.thinking, agent.effort = "omit", None
    enrich_items(agent, [Article(id="a", category="article", source_name="S", title="T", url="https://x")], "short")
    assert "thinking" not in agent.client.calls[0] and "output_config" not in agent.client.calls[0]


def test_refusal_raises_agent_error():
    agent = make_agent([response([], stop_reason="refusal")])
    with pytest.raises(AgentError, match="declined"):
        agent.structured("s", "u", {"name": "x", "description": "", "input_schema": {"type": "object"}})


def test_sonnet_5_5_pricing():
    agent = make_agent(echo_summaries)
    agent.model = "claude-sonnet-5-5"
    p = agent.price()
    assert (p.input, p.output, p.cache_read_mult) == (2.0, 10.0, 0.05)


def test_run_tools_gives_up():
    agent = make_agent(lambda kw: response([text("nope")], stop_reason="end_turn"))
    with pytest.raises(AgentError):
        agent.run_tools("s", "u", [], {"name": "submit", "description": "", "input_schema": {}}, max_turns=2)


def test_budget_exceeded_raises():
    agent = make_agent([], max_usd=0)
    with pytest.raises(BudgetExceeded):
        agent.structured("s", "u", {"name": "x", "description": "", "input_schema": {}})


def test_web_collector_validates_domain_and_dates(ctx_factory):
    submitted = {
        "items": [
            {"title": "Good", "url": "https://claude.dev/blog/good", "published_at": "2025-11-04"},
            {"title": "Off-domain", "url": "https://evil.com/x", "published_at": "2025-11-04"},
            {"title": "Too old", "url": "https://claude.dev/blog/old", "published_at": "2025-10-01"},
            {"title": "No date", "url": "https://claude.dev/blog/nodate", "published_at": "unknown"},
        ]
    }
    agent = make_agent([response([tool_use("submit_items", submitted)])])
    ctx = ctx_factory({}, agent=agent)
    items = collect_web(
        ctx, ArticleSource(name="cd", type="web", url="https://claude.dev/blog", lookback_days=7), "article"
    )
    assert [i.title for i in items] == ["Good"]
    tools = agent.client.calls[0]["tools"]
    assert tools[0]["type"] == "web_fetch_20250910" and tools[0]["allowed_domains"] == ["claude.dev"]


FEATURE_SRC = FeatureSource(name="Davao", location="Davao City, Philippines", freshness_days=365)


def _place(name, date="2025-06-01"):
    return {
        "place_name": name,
        "address": "123 Street",
        "description": "Cozy.",
        "why_featured": "Great coffee.",
        "must_try": ["Latte"],
        "sources": [{"url": "https://blog.example.com/x", "title": "Review", "date": date}],
    }


def test_feature_accepts_fresh_place(ctx_factory):
    agent = make_agent([response([tool_use("submit_feature", {"places": [_place("Bean There")]})])])
    ctx = ctx_factory({}, agent=agent)
    [feat] = collect_feature(ctx, FEATURE_SRC)
    assert feat.place_name == "Bean There"
    assert feat.map_url.startswith("https://www.google.com/maps/search/")
    assert feat.sources[0].date == "2025-06-01"
    tools = agent.client.calls[0]["tools"]
    assert {t["name"] for t in tools} == {"web_search", "web_fetch", "submit_feature"}


def test_feature_rejects_stale_and_repeat_then_retries(ctx_factory):
    ledger = Ledger()
    ledger.data["features"][feature_key("Old Favorite", "Davao City")] = "2025-01-01"
    queue = [
        response([tool_use("submit_feature", {"places": [_place("Old Favorite")]})]),
        response([tool_use("submit_feature", {"places": [_place("Stale Spot", date="2023-01-01")]})]),
    ]
    agent = make_agent(queue)
    ctx = ctx_factory({}, agent=agent, ledger=ledger)
    with pytest.raises(AgentError, match="Stale Spot"):
        collect_feature(ctx, FEATURE_SRC)
    # Second attempt was told why the first was rejected and which places to avoid.
    retry_user = agent.client.calls[1]["messages"][0]["content"]
    assert "already featured" in retry_user
    assert "old favorite" in agent.client.calls[1]["system"][0]["text"]


@pytest.mark.parametrize("name", ["ENRICH_TOOL", "WEB_SUBMIT_TOOL", "FEATURE_SUBMIT_TOOL"])
def test_output_schemas_are_strict_compatible(name):
    from daily_briefing.agent import prompts
    from daily_briefing.agent.client import strict_tool

    def walk(s):
        if isinstance(s, dict):
            if s.get("type") == "object":
                assert s["additionalProperties"] is False
                assert set(s["required"]) == set(s["properties"])
            for k, v in s.items():
                assert k not in ("minimum", "maximum", "minLength", "maxLength", "maxItems")
                walk(v)
        elif isinstance(s, list):
            for v in s:
                walk(v)

    walk(strict_tool(getattr(prompts, name))["input_schema"])
