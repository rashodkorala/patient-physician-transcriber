"""Week 1 plain translation path.

Development only: every result is `final`. Read-back, blocking, and escalation arrive
with the turn graph (ADR-004, task 2.3) and read-back (task 2.6) before any rehearsal.

@implements ADR-006: LLM: Claude Sonnet 5.5 for live turns, Opus 5.5 for note and summary
@implements EDR-002: Testing: pytest with mocked LLM, speaker-rated tone set, latency check
@see openspec/tdr/adr/adr-006-llm-models.md
"""

from typing import Protocol

import anthropic
from pydantic import BaseModel

from config import LIVE_MODEL
from contracts import Certainty, Emotion, Language, Speaker, ToneTag

LANGUAGE_NAMES = {"pa-IN": "Punjabi (Gurmukhi script)", "fr-CA": "Canadian French", "en-CA": "English"}


class TranslationOutput(BaseModel):
    translation: str
    back_translation: str
    tone_tags: list[ToneTag]
    emotion: Emotion
    certainty: Certainty
    confidence: float


class TranslationRefused(Exception):
    pass


class Translator(Protocol):
    async def translate(
        self, text: str, source: Language, target: Language, speaker: Speaker
    ) -> TranslationOutput: ...


SYSTEM_PROMPT = """You interpret a medical consultation between a patient and a physician who do not share a language.
Translate the speaker's words faithfully into the target language for the listener.
- Keep the speaker's level of certainty: never make news sound more or less serious than it was said.
- Keep warmth and reassurance; use the respectful form of address customary in the target language.
- Never change numbers, doses, units, frequencies, dates, or medication names.
- Then translate your translation back into the source language as back_translation.
- tone_tags describe the register of your translation; emotion describes the speaker; confidence (0 to 1) is how sure you are the meaning was kept."""


class ClaudeTranslator:
    def __init__(self, client: anthropic.AsyncAnthropic | None = None) -> None:
        self.client = client or anthropic.AsyncAnthropic()

    async def translate(
        self, text: str, source: Language, target: Language, speaker: Speaker
    ) -> TranslationOutput:
        response = await self.client.beta.messages.parse(
            model=LIVE_MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            # Live turns favour latency (target under 3 seconds); tune with the tone set (EDR-002).
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Speaker: {speaker}\n"
                        f"Source language: {LANGUAGE_NAMES[source]}\n"
                        f"Target language: {LANGUAGE_NAMES[target]}\n"
                        f"Utterance: {text}"
                    ),
                }
            ],
            output_format=TranslationOutput,
        )
        if response.stop_reason == "refusal" or response.parsed_output is None:
            raise TranslationRefused(f"stop_reason={response.stop_reason}")
        return response.parsed_output


class FakeTranslator:
    """Deterministic stand-in for tests and keyless runs (EDR-002)."""

    async def translate(
        self, text: str, source: Language, target: Language, speaker: Speaker
    ) -> TranslationOutput:
        return TranslationOutput(
            translation=f"[{target}] {text}",
            back_translation=text,
            tone_tags=["respectful"],
            emotion="calm",
            certainty="high",
            confidence=0.99,
        )
