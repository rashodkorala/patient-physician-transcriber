"""ClaudeModel request shape with a mocked SDK client (ADR-004, ADR-006, EDR-002)."""

import asyncio
from types import SimpleNamespace

import pytest

from config import LIVE_MODEL
from graph.turn_graph import Draft
from llm import ClaudeModel, ModelRefused

DRAFT = Draft(
    translation="Bonjour, docteur.", back_translation="Hello, doctor.", tone_tags=["respectful"], confidence=0.95
)


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    async def parse(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def client_with(response):
    messages = FakeMessages(response)
    return SimpleNamespace(beta=SimpleNamespace(messages=messages)), messages


def test_live_model_structured_output_and_refusal_fallback_adr_006():
    client, messages = client_with(SimpleNamespace(stop_reason="end_turn", parsed_output=DRAFT))
    out = asyncio.run(ClaudeModel(client=client).parse(purpose="translate", system="s", user="u", schema=Draft))
    assert out == DRAFT
    assert messages.kwargs["model"] == LIVE_MODEL == "claude-sonnet-5-5"
    assert messages.kwargs["output_format"] is Draft
    assert messages.kwargs["fallbacks"] == "default"
    assert messages.kwargs["betas"] == ["server-side-fallback-2026-07-01"]
    assert messages.kwargs["output_config"] == {"effort": "low"}


def test_refusal_raises_so_nothing_is_spoken():
    client, _ = client_with(SimpleNamespace(stop_reason="refusal", parsed_output=None))
    with pytest.raises(ModelRefused):
        asyncio.run(ClaudeModel(client=client).parse(purpose="translate", system="s", user="u", schema=Draft))
