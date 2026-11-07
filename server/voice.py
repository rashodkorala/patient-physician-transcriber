"""The interpreter's voice: ElevenLabs speech streamed by the server, for checked text only.

The browser never sends text to speak. It asks for a turn or line by id, and the server decides
whether that id may be spoken (see main.py), so a failed check can never reach the speaker.
Delivery follows the turn's emotion and certainty through a fixed table, never a model's words.

@implements ADR-010: Voice output: ElevenLabs Eleven v4 replaces OpenAI text-to-speech; Azure stays fallback
@implements CDR-003: Participant names and interpreter lines on the visit channel
@see openspec/tdr/adr/adr-010-elevenlabs-voice-output.md
"""

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Protocol, get_args

from contracts import Certainty, Emotion, Language

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


# Emotion is the speaker's; the interpreter answers it the way a person would, calm and steady
# with someone worried or in pain, warm with someone relieved, patient with someone confused.
EMOTION_DELIVERY: dict[str, Delivery] = {
    "calm": Delivery("[calm]", 0.5),
    "worried": Delivery("[gently]", 0.65),
    "embarrassed": Delivery("[softly]", 0.6),
    "in_pain": Delivery("[gently]", 0.65),
    "relieved": Delivery("[warmly]", 0.45),
    "confused": Delivery("[patiently]", 0.6),
}
# Certain content is said steadily; uncertain content keeps the emotion's own setting, since an
# interpreter never sounds unsure on the speaker's behalf.
CERTAINTY_STEADINESS: dict[str, float] = {"high": 0.1, "medium": 0.0, "low": 0.0}
# The interpreter's own lines (introduction, name questions, welcome).
LINE_DELIVERY = Delivery("[warmly]", 0.5)

assert set(EMOTION_DELIVERY) == set(get_args(Emotion)), "every emotion needs a delivery"
assert set(CERTAINTY_STEADINESS) == set(get_args(Certainty)), "every certainty needs a steadiness"


def delivery_for(emotion: str, certainty: str) -> Delivery:
    base = EMOTION_DELIVERY[emotion]
    return Delivery(base.tag, min(1.0, base.stability + CERTAINTY_STEADINESS[certainty]))


def spoken_text(text: str, delivery: Delivery) -> str:
    """The tag goes first; square brackets in the text itself would be read as tags, so they become round."""
    return f"{delivery.tag} {text.replace('[', '(').replace(']', ')')}"


class VoiceUnavailable(Exception):
    """The server voice cannot speak this; the browser falls back to Azure."""


class Voice(Protocol):
    name: str

    def supports(self, language: Language) -> bool: ...

    async def stream(self, text: str, language: Language, delivery: Delivery) -> AsyncIterator[bytes]:
        """Audio chunks; raises VoiceUnavailable before the first chunk if the vendor fails."""
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

    async def stream(self, text: str, language: Language, delivery: Delivery) -> AsyncIterator[bytes]:
        from elevenlabs import VoiceSettings

        if not self.supports(language):
            raise VoiceUnavailable(f"No ElevenLabs voice for {language}")
        await self.slots.acquire()
        chunks = self.tts.stream(
            self.voice_id,
            text=spoken_text(text, delivery),
            model_id=self.model,
            language_code=LANGUAGE_CODES[language],
            voice_settings=VoiceSettings(stability=delivery.stability),
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
