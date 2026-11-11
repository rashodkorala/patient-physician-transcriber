"""ClaudeModel request shape and client settings with a mocked SDK client (ADR-004, ADR-006, EDR-002)."""

import asyncio
from types import SimpleNamespace

import pytest

import llm
from config import LIVE_MODEL, TONE_MODEL
from graph.turn_graph import Draft, ToneCheck
from llm import DEFAULT_MODELS_BY_PURPOSE, LIVE_TIMEOUT_S, MAX_RETRIES, ClaudeModel, ModelRefused
from trust import CultureCueDraft

DRAFT = Draft(
    emotion="calm",
    certainty="high",
    manner="plain",
    medications=[],
    translation="Bonjour, docteur.",
    back_translation="Hello, doctor.",
    tone_tags=["respectful"],
    confidence=0.95,
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
    return SimpleNamespace(beta=SimpleNamespace(messages=messages), messages=FakeMessages(None)), messages


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


def test_tone_check_runs_on_haiku_without_the_fallback_beta_adr_006():
    tone = ToneCheck(meaning_preserved=True, certainty_preserved=True, warmth_preserved=True, issue="")
    plain = FakeMessages(SimpleNamespace(stop_reason="end_turn", parsed_output=tone))
    beta = FakeMessages(None)
    client = SimpleNamespace(messages=plain, beta=SimpleNamespace(messages=beta))
    out = asyncio.run(ClaudeModel(client=client).parse(purpose="tone_check", system="s", user="u", schema=ToneCheck))
    assert out == tone and beta.kwargs is None  # the beta endpoint was never called
    assert plain.kwargs["model"] == TONE_MODEL == "claude-haiku-5-5"
    assert "fallbacks" not in plain.kwargs and "betas" not in plain.kwargs
    assert plain.kwargs["output_config"] == {"effort": "low"} and plain.kwargs["output_format"] is ToneCheck


def test_trust_advisor_runs_on_the_tone_model_adr_006_mdd_005():
    assert DEFAULT_MODELS_BY_PURPOSE["trust"] == TONE_MODEL
    draft = CultureCueDraft(cue=None)
    plain = FakeMessages(SimpleNamespace(stop_reason="end_turn", parsed_output=draft))
    client = SimpleNamespace(messages=plain, beta=SimpleNamespace(messages=FakeMessages(None)))
    out = asyncio.run(ClaudeModel(client=client).parse(purpose="trust", system="s", user="u", schema=CultureCueDraft))
    assert out == draft and plain.kwargs["model"] == TONE_MODEL


def test_default_client_gives_up_after_25_seconds_with_two_retries_adr_004(monkeypatch):
    """A hung live call ends the turn as `failed` instead of hanging the visit (trust-across-the-barrier 2.8)."""
    captured: dict = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(llm.anthropic, "AsyncAnthropic", FakeClient)
    assert isinstance(ClaudeModel().client, FakeClient)
    assert captured == {"timeout": LIVE_TIMEOUT_S, "max_retries": MAX_RETRIES} == {"timeout": 25.0, "max_retries": 2}
    # A client passed in keeps its own settings.
    captured.clear()
    ClaudeModel(client=object())
    assert captured == {}
