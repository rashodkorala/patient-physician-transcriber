"""Translator tests with a mocked SDK client (EDR-002: no real AI calls in unit tests)."""

import asyncio
from types import SimpleNamespace

import pytest

from config import LIVE_MODEL
from translate import ClaudeTranslator, TranslationOutput, TranslationRefused


class FakeBetaMessages:
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    async def parse(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def make_client(response):
    messages = FakeBetaMessages(response)
    return SimpleNamespace(beta=SimpleNamespace(messages=messages)), messages


OUTPUT = TranslationOutput(
    translation="Bonjour, docteur.", back_translation="Hello, doctor.", tone_tags=["respectful"],
    emotion="calm", certainty="high", confidence=0.95,
)


def test_uses_live_model_structured_output_and_fallback_adr_006():
    client, messages = make_client(SimpleNamespace(stop_reason="end_turn", parsed_output=OUTPUT))
    out = asyncio.run(ClaudeTranslator(client).translate("Hello, doctor.", "en-CA", "fr-CA", "patient"))
    assert out == OUTPUT
    assert messages.kwargs["model"] == LIVE_MODEL == "claude-sonnet-5-5"
    assert messages.kwargs["output_format"] is TranslationOutput
    assert messages.kwargs["fallbacks"] == "default"
    assert "Canadian French" in messages.kwargs["messages"][0]["content"]


def test_refusal_raises_so_nothing_is_spoken():
    client, _ = make_client(SimpleNamespace(stop_reason="refusal", parsed_output=None))
    with pytest.raises(TranslationRefused):
        asyncio.run(ClaudeTranslator(client).translate("x", "en-CA", "pa-IN", "physician"))
