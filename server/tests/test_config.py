"""Settings tests: a live run never falls back to the fake model silently (ADR-006, EDR-002), and the
services the controller shows match what the server runs (ADR-006, ADR-010)."""

import pytest
from fastapi.testclient import TestClient

from config import LIVE_MODEL, RECORD_MODEL, TONE_MODEL, Settings, load_settings
from kb.embeddings import HashingEmbedder
from kb.store import KnowledgeBase
from main import create_app, describe, services
from voice import DEFAULT_MODEL, DEFAULT_VOICE

AZURE = {"azure_speech_key": "key", "azure_speech_region": "canadacentral"}


class StubVoice:
    """Stands in for ElevenLabsVoice: only the ids services() reads."""

    def __init__(self, model: str = "eleven_v4", voice_id: str = "voice-1") -> None:
        self.model = model
        self.voice_id = voice_id


@pytest.fixture
def env(monkeypatch):
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "TRANSLATOR", "TEST_LANGUAGES"):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_blank_translator_with_a_key_is_claude(env):
    # scripts/dev.sh exports every line of .env, so TRANSLATOR= arrives as an empty string.
    env.setenv("ANTHROPIC_API_KEY", "sk-test")
    env.setenv("TRANSLATOR", "")
    assert load_settings().translator == "claude"


def test_no_key_is_fake(env):
    assert load_settings().translator == "fake"


def test_explicit_fake_wins_over_a_key(env):
    env.setenv("ANTHROPIC_API_KEY", "sk-test")
    env.setenv("TRANSLATOR", "fake")
    assert load_settings().translator == "fake"


def test_unknown_translator_stops_start_up(env):
    env.setenv("TRANSLATOR", "cluade")
    with pytest.raises(ValueError, match="TRANSLATOR"):
        load_settings()


def test_test_languages_off_by_default_tdm_003(env):
    assert load_settings().test_languages is False


@pytest.mark.parametrize(("value", "on"), [("on", True), ("ON", True), ("1", True), ("", False), ("off", False)])
def test_test_languages_start_up_setting_tdm_003(env, value, on):
    env.setenv("TEST_LANGUAGES", value)
    assert load_settings().test_languages is on


# ---------- the services line (ADR-006, ADR-010) ----------


def fake_settings() -> Settings:
    return Settings(translator="fake", azure_speech_key=None, azure_speech_region=None)


def test_services_claude_names_the_three_models_adr_006():
    used = services(Settings(translator="claude", **AZURE), StubVoice(), HashingEmbedder())
    assert (used["translator"], used["liveModel"], used["toneModel"], used["recordModel"]) == (
        "claude",
        LIVE_MODEL,
        TONE_MODEL,
        RECORD_MODEL,
    )
    assert used["recognition"] == "azure"
    assert all(isinstance(v, str) for v in used.values())


def test_services_fake_names_no_models_adr_006():
    used = services(fake_settings(), None, HashingEmbedder())
    assert used["translator"] == "fake"
    assert used["liveModel"] == used["toneModel"] == used["recordModel"] == ""
    assert used["recognition"] == "none"
    assert used["embeddings"] == "hashing"
    assert "fake model (no AI calls)" in describe(used, test_languages=False)


def test_services_voice_present_adr_006_adr_010():
    used = services(Settings(translator="claude", **AZURE), StubVoice("eleven_v4", "abc"), HashingEmbedder())
    assert (used["voice"], used["voiceModel"], used["voiceId"]) == ("elevenlabs", "eleven_v4", "abc")
    # A voice without ids of its own falls back to the settings, then the defaults.
    used = services(Settings(translator="claude", **AZURE), object(), HashingEmbedder())
    assert (used["voiceModel"], used["voiceId"]) == (DEFAULT_MODEL, DEFAULT_VOICE)


def test_services_voice_absent_adr_006_adr_010():
    with_azure = services(Settings(translator="claude", **AZURE), None, HashingEmbedder())
    assert (with_azure["voice"], with_azure["voiceModel"], with_azure["voiceId"]) == ("azure", "", "")
    assert services(fake_settings(), None, HashingEmbedder())["voice"] == "none"


def test_health_reports_services_adr_006():
    settings = fake_settings()
    kb = KnowledgeBase(HashingEmbedder())
    with TestClient(create_app(settings=settings, kb=kb)) as client:
        health = client.get("/api/health").json()
    assert health["services"] == services(settings, None, kb.embedder)
    # The old top-level field stays as it was for compatibility.
    assert health["voice"] == "azure" and health["services"]["voice"] == "none"
