"""Settings tests: a live run never falls back to the fake model silently (ADR-006, EDR-002)."""

import pytest

from config import load_settings


@pytest.fixture
def env(monkeypatch):
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "TRANSLATOR"):
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
