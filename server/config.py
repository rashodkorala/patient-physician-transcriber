"""Server settings and model ids.

@implements ADR-006: LLM: Claude Sonnet 5.5 for live turns, Opus 5.5 for note and summary
@implements TDM-003: Sinhala and Tamil as test-only languages before demo night
@implements ADR-010: Voice output: ElevenLabs Eleven v4 replaces OpenAI text-to-speech; Azure stays fallback
@see openspec/tdr/adr/adr-006-llm-models.md
"""

import os
from dataclasses import dataclass

# ADR-006: model ids live here only; nodes and chains import them.
LIVE_MODEL = "claude-sonnet-5-5"
RECORD_MODEL = "claude-opus-5-5"
# ADR-006 amended 2026-10-25: the tone check is a yes or no judgement, so it runs on Haiku for latency.
TONE_MODEL = "claude-haiku-5-5"


@dataclass(frozen=True)
class Settings:
    translator: str
    azure_speech_key: str | None
    azure_speech_region: str | None
    # TDM-003: Sinhala selectable only when the server starts with TEST_LANGUAGES=on (Tamil is live, TDM-004).
    # Read once at start-up; there is deliberately no way to change it while running.
    test_languages: bool = False
    # ADR-010: the server voice. Without a key the browser speaks with Azure, as before.
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str | None = None
    elevenlabs_model: str | None = None


TRANSLATORS = ("claude", "fake")


def load_settings() -> Settings:
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    # A blank TRANSLATOR= line in .env counts as unset: "claude" when credentials exist, else
    # "fake" so the app runs without keys (EDR-002). Anything else is a typo and stops start-up,
    # so a live run can never fall back to the fake model silently.
    translator = os.environ.get("TRANSLATOR", "").strip().lower() or ("claude" if has_key else "fake")
    if translator not in TRANSLATORS:
        raise ValueError(f"TRANSLATOR must be one of {', '.join(TRANSLATORS)}, not {translator!r}")
    return Settings(
        translator=translator,
        azure_speech_key=os.environ.get("AZURE_SPEECH_KEY") or None,
        azure_speech_region=os.environ.get("AZURE_SPEECH_REGION") or None,
        test_languages=os.environ.get("TEST_LANGUAGES", "").strip().lower() in ("on", "1", "true", "yes"),
        elevenlabs_api_key=os.environ.get("ELEVENLABS_API_KEY") or None,
        elevenlabs_voice_id=os.environ.get("ELEVENLABS_VOICE_ID") or None,
        elevenlabs_model=os.environ.get("ELEVENLABS_MODEL") or None,
    )
