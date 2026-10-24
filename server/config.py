"""Server settings and model ids.

@implements ADR-006: LLM: Claude Sonnet 5.5 for live turns, Opus 5.5 for note and summary
@see openspec/tdr/adr/adr-006-llm-models.md
"""

import os
from dataclasses import dataclass

# ADR-006: model ids live here only; nodes and chains import them.
LIVE_MODEL = "claude-sonnet-5-5"
RECORD_MODEL = "claude-opus-5-5"


@dataclass(frozen=True)
class Settings:
    translator: str
    azure_speech_key: str | None
    azure_speech_region: str | None


def load_settings() -> Settings:
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    return Settings(
        # "claude" when credentials exist, else "fake" so the app runs without keys (EDR-002).
        translator=os.environ.get("TRANSLATOR", "claude" if has_key else "fake"),
        azure_speech_key=os.environ.get("AZURE_SPEECH_KEY") or None,
        azure_speech_region=os.environ.get("AZURE_SPEECH_REGION") or None,
    )
