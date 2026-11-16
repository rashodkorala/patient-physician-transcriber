"""The interpreter's voice: ElevenLabs speech streamed by the server, for checked text only.

The browser never sends text to speak. It asks for a turn or line by id, and the server decides
whether that id may be spoken (see main.py), so a failed check can never reach the speaker.
Every turn, in both directions, and every interpreter line is said in one constant delivery (IDR-006): tone
tags did not carry affect, so a patient's affect is carried in the words instead, as one hedged phrase in the
relay's reporting frame, and certainty is carried by the words only.

@implements ADR-010: Voice output: ElevenLabs Eleven v4 replaces OpenAI text-to-speech; Azure stays fallback
@implements CDR-003: Participant names and interpreter lines on the visit channel
@implements MDD-006: Affect in words
@implements IDR-006: Affect phrase in the reporting frame, and one constant voice delivery
@see openspec/tdr/adr/adr-010-elevenlabs-voice-output.md
@see openspec/tdr/idr/idr-006-affect-phrase-in-the-frame-and-constant-voice.md
"""

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Protocol

from contracts import Language

# Sarah, an account voice: library voices need a paid plan through the API.
DEFAULT_VOICE = "EXAVITQu4vr4xnSDxMaL"
DEFAULT_MODEL = "eleven_v4"
OUTPUT_FORMAT = "mp3_44100_128"
# The free and starter plans allow two requests at once; more get a 429. Requests beyond this wait.
DEFAULT_CONCURRENCY = 2

# ISO 639-1 codes ElevenLabs lists for Eleven v4. Sinhala is not listed, so a Sinhala visit is
# spoken by the browser's Azure voice instead (TDM-003).
LANGUAGE_CODES: dict[str, str] = {"pa-IN": "pa", "fr-CA": "fr", "en-CA": "en", "ta-LK": "ta"}


@dataclass(frozen=True)
class Delivery:
    """How a line is said: an audio tag the model performs (never speaks) and a stability value."""

    tag: str
    stability: float


# IDR-006: the one delivery for everything the interpreter says, whoever spoke and however they said it; the
# former plain setting, so the interpreter sounds like an interpreter at work.
DELIVERY = Delivery("[calm]", 0.55)


def spoken_text(text: str) -> str:
    """The tag goes first; square brackets in the text itself would be read as tags, so they become round."""
    return f"{DELIVERY.tag} {text.replace('[', '(').replace(']', ')')}"


class VoiceUnavailable(Exception):
    """The server voice cannot speak this; the browser falls back to Azure."""


class Voice(Protocol):
    name: str

    def supports(self, language: Language) -> bool: ...

    async def stream(self, text: str, language: Language) -> AsyncIterator[bytes]:
        """Audio chunks in the constant delivery; raises VoiceUnavailable before the first chunk if the vendor fails."""
        ...


class ElevenLabsVoice:
    name = "ElevenLabs"

    def __init__(
        self,
        api_key: str,
        voice_id: str = DEFAULT_VOICE,
        model: str = DEFAULT_MODEL,
        concurrency: int = DEFAULT_CONCURRENCY,
    ) -> None:
        from elevenlabs import AsyncElevenLabs

        # Passed explicitly: the SDK's own environment lookup happens at import time.
        self.tts = AsyncElevenLabs(api_key=api_key).text_to_speech
        self.voice_id = voice_id
        self.model = model
        # Held for a whole stream, so lines asked for together queue here instead of failing.
        self.slots = asyncio.Semaphore(concurrency)

    def supports(self, language: Language) -> bool:
        return language in LANGUAGE_CODES

    async def stream(self, text: str, language: Language) -> AsyncIterator[bytes]:
        from elevenlabs import VoiceSettings

        if not self.supports(language):
            raise VoiceUnavailable(f"No ElevenLabs voice for {language}")
        await self.slots.acquire()
        chunks = self.tts.stream(
            self.voice_id,
            text=spoken_text(text),
            model_id=self.model,
            language_code=LANGUAGE_CODES[language],
            voice_settings=VoiceSettings(stability=DELIVERY.stability),
            output_format=OUTPUT_FORMAT,
        )
        # Pull the first chunk here, so a vendor failure is a clean error the browser can fall back
        # from, rather than an audio stream that breaks after it has started.
        try:
            first = await anext(chunks)
        except StopAsyncIteration as exc:
            self.slots.release()
            raise VoiceUnavailable("ElevenLabs returned no audio") from exc
        except Exception as exc:  # API error, quota, or network: all mean fall back
            self.slots.release()
            raise VoiceUnavailable(f"ElevenLabs failed: {describe_error(exc)}") from exc
        return _rest(first, chunks, self.slots.release)


def describe_error(exc: Exception) -> str:
    """The status and the vendor's own message, without the response headers the SDK includes."""
    status = getattr(exc, "status_code", None)
    body = getattr(exc, "body", None)
    detail = body.get("detail") if isinstance(body, dict) else None
    message = detail.get("message") if isinstance(detail, dict) else detail
    return f"{status} {message}" if status else str(exc)


async def _rest(first: bytes, rest: AsyncIterator[bytes], done: Callable[[], None]) -> AsyncIterator[bytes]:
    """Reads the vendor stream at its own pace and frees the slot when the vendor finishes.

    The browser reads a line's audio only when that line's turn to play comes, so tying the slot to
    the browser would hold it for a queued line and stall every line after it.
    """
    buffered: asyncio.Queue[bytes | None] = asyncio.Queue()
    buffered.put_nowait(first)

    async def pump() -> None:
        try:
            async for chunk in rest:
                buffered.put_nowait(chunk)
        finally:
            done()
            buffered.put_nowait(None)

    # Kept referenced until it ends; it runs on even if the browser goes away, then frees the slot.
    task = asyncio.create_task(pump())
    _pumps.add(task)
    task.add_done_callback(_pumps.discard)
    while (chunk := await buffered.get()) is not None:
        yield chunk


_pumps: set[asyncio.Task] = set()
