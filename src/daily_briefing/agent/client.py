"""Thin wrapper over the Anthropic SDK: structured outputs, tool loops, cost + budget tracking.

Written for Claude Sonnet 5.5 semantics, which also work on older models:
- No forced ``tool_choice`` (Sonnet 5.5 rejects ``any``/``tool``). Output tools are ``strict`` and the
  prompt tells the model when to call them; if it doesn't, we nudge it.
- Content blocks (including ``thinking``) are read by type and passed back unchanged.
"""

from __future__ import annotations

import copy
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..config import ModelPricing

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Price:
    input: float  # USD / MTok
    output: float
    cache_read_mult: float = 0.10
    cache_write_mult: float = 1.25  # 5-minute cache writes


# Prefix-matched against the model id (most specific first). Source: Claude pricing page, Nov 2026.
PRICING: list[tuple[str, Price]] = [
    ("claude-sonnet-5-5", Price(2.0, 10.0, cache_read_mult=0.05)),
    ("claude-opus-5-5", Price(4.0, 20.0, cache_read_mult=0.05)),
    ("claude-haiku-5-5", Price(0.10, 0.50)),
    ("claude-sonnet-5", Price(2.0, 10.0)),
    ("claude-opus-5", Price(5.0, 25.0)),
    ("claude-sonnet-4-6", Price(3.0, 15.0)),
    ("claude-sonnet-4", Price(3.0, 15.0)),
    ("claude-haiku-4", Price(1.0, 5.0)),
    ("claude-opus-4-5", Price(5.0, 25.0)),
    ("claude-opus-4-6", Price(5.0, 25.0)),
]
DEFAULT_PRICE = Price(3.0, 15.0)
WEB_SEARCH_USD = 10.0 / 1000


class BudgetExceeded(RuntimeError):
    pass


class AgentError(RuntimeError):
    pass


def strict_tool(tool: dict) -> dict:
    """Return a copy of a tool definition prepared for strict tool use."""

    def fix(schema: Any) -> Any:
        if isinstance(schema, dict):
            schema = {k: fix(v) for k, v in schema.items()}
            if schema.get("type") == "object":
                schema["additionalProperties"] = False
            return schema
        if isinstance(schema, list):
            return [fix(s) for s in schema]
        return schema

    out = copy.deepcopy(tool)
    out["input_schema"] = fix(out["input_schema"])
    out["strict"] = True
    return out


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    web_searches: int = 0
    web_fetches: int = 0
    cost_usd: float = 0.0


@dataclass
class Agent:
    client: Any  # anthropic.Anthropic (or a fake with .messages.create)
    model: str
    max_usd: float
    pricing_override: ModelPricing | None = None
    thinking: str = "between_tools"  # between_tools | adaptive | omit
    effort: str | None = "medium"
    usage: Usage = field(default_factory=Usage)

    # ------------------------------------------------------------------ cost
    def price(self) -> Price:
        if self.pricing_override:
            p = self.pricing_override
            return Price(p.input_per_mtok, p.output_per_mtok, cache_read_mult=p.cache_read_multiplier)
        for prefix, p in PRICING:
            if self.model.startswith(prefix):
                return p
        return DEFAULT_PRICE

    def _record(self, resp: Any) -> None:
        u = getattr(resp, "usage", None)
        if u is None:
            return
        p = self.price()
        cw = getattr(u, "cache_creation_input_tokens", 0) or 0
        cr = getattr(u, "cache_read_input_tokens", 0) or 0
        stu = getattr(u, "server_tool_use", None)
        searches = (getattr(stu, "web_search_requests", 0) or 0) if stu else 0
        fetches = (getattr(stu, "web_fetch_requests", 0) or 0) if stu else 0
        cost = (
            u.input_tokens * p.input
            + cw * p.input * p.cache_write_mult
            + cr * p.input * p.cache_read_mult
            + u.output_tokens * p.output
        ) / 1_000_000 + searches * WEB_SEARCH_USD
        s = self.usage
        s.calls += 1
        s.input_tokens += u.input_tokens
        s.output_tokens += u.output_tokens
        s.cache_write_tokens += cw
        s.cache_read_tokens += cr
        s.web_searches += searches
        s.web_fetches += fetches
        s.cost_usd += cost

    @property
    def exhausted(self) -> bool:
        return self.usage.cost_usd >= self.max_usd

    def _create(self, **kwargs) -> Any:
        if self.exhausted:
            raise BudgetExceeded(f"budget of ${self.max_usd:.2f} reached")
        if self.thinking != "omit":
            kwargs["thinking"] = {"type": self.thinking}
        if self.effort:
            kwargs["output_config"] = {"effort": self.effort}
        resp = self.client.messages.create(model=self.model, **kwargs)
        self._record(resp)
        if getattr(resp, "stop_reason", None) == "refusal":
            details = getattr(resp, "stop_details", None)
            raise AgentError(f"model declined the request ({details})")
        return resp

    @staticmethod
    def _system(text: str) -> list[dict]:
        return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]

    @staticmethod
    def _find_tool_use(resp: Any, name: str) -> dict | None:
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use" and block.name == name:
                return dict(block.input)
        return None

    # ------------------------------------------------------------ structured
    def structured(self, system: str, user: str, tool: dict, max_tokens: int = 8000, attempts: int = 2) -> dict:
        """Get a single structured answer by having the model call ``tool``."""
        tool_def = {**strict_tool(tool), "cache_control": {"type": "ephemeral"}}
        messages: list[dict] = [{"role": "user", "content": user}]
        resp = None
        for _ in range(attempts):
            resp = self._create(
                max_tokens=max_tokens,
                system=self._system(system),
                tools=[tool_def],
                tool_choice={"type": "auto"},
                messages=list(messages),
            )
            found = self._find_tool_use(resp, tool["name"])
            if found is not None:
                return found
            messages.append({"role": "assistant", "content": resp.content})
            messages.append({"role": "user", "content": f"Call the {tool['name']} tool with your answer."})
        raise AgentError(f"model did not call {tool['name']} (stop_reason={getattr(resp, 'stop_reason', None)})")

    # ------------------------------------------------------------- tool loop
    def run_tools(
        self,
        system: str,
        user: str,
        tools: list[dict],
        submit_tool: dict,
        handlers: dict[str, Callable[[dict], str]] | None = None,
        max_turns: int = 15,
        max_tokens: int = 16000,
    ) -> dict:
        """Agentic loop: server tools run on Anthropic's side, custom tools via ``handlers``.

        Ends when the model calls ``submit_tool``; returns that tool's input.
        """
        handlers = handlers or {}
        submit = submit_tool["name"]
        all_tools = [*tools, {**strict_tool(submit_tool), "cache_control": {"type": "ephemeral"}}]
        messages: list[dict] = [{"role": "user", "content": user}]
        for turn in range(max_turns):
            resp = self._create(
                max_tokens=max_tokens,
                system=self._system(system),
                tools=all_tools,
                tool_choice={"type": "auto"},
                messages=list(messages),
            )
            messages.append({"role": "assistant", "content": resp.content})

            user_blocks: list[dict] = []
            for block in resp.content:
                if getattr(block, "type", None) != "tool_use":
                    continue
                if block.name == submit:
                    return dict(block.input)
                handler = handlers.get(block.name)
                try:
                    out = handler(dict(block.input)) if handler else f"unknown tool {block.name}"
                    is_error = handler is None
                except Exception as e:  # report tool failures back to the model
                    out, is_error = f"error: {e}", True
                user_blocks.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": out, "is_error": is_error}
                )

            if resp.stop_reason == "pause_turn" and not user_blocks:
                continue  # server-side tool loop paused; resend so it can continue
            nearly_out = turn >= max_turns - 2
            if not user_blocks or nearly_out:
                note = (
                    f"You are out of steps. Call {submit} now with the best answer you have."
                    if nearly_out
                    else f"When you are done, call the {submit} tool with your final answer."
                )
                user_blocks.append({"type": "text", "text": note})
            messages.append({"role": "user", "content": user_blocks})
        raise AgentError(f"agent did not call {submit} within {max_turns} turns")


def make_agent(
    api_key: str,
    model: str,
    max_usd: float,
    pricing: ModelPricing | None = None,
    thinking: str = "between_tools",
    effort: str | None = "medium",
) -> Agent:
    import anthropic

    return Agent(
        client=anthropic.Anthropic(api_key=api_key, max_retries=3),
        model=model,
        max_usd=max_usd,
        pricing_override=pricing,
        thinking=thinking,
        effort=effort,
    )
