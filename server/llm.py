"""One way to call Claude for every node and chain, plus a scripted stand-in for tests.

@implements ADR-004: LangGraph turn graph; model calls use the official anthropic SDK
@implements ADR-006: LLM: Claude Sonnet 5.5 for live turns, Opus 5.5 for note and summary
@implements EDR-002: Testing: pytest with mocked LLM
@see openspec/tdr/adr/adr-004-langgraph-turn-graph.md
"""

import logging
import time
from collections.abc import Callable
from typing import Any, Protocol, TypeVar

import anthropic
from pydantic import BaseModel

from config import LIVE_MODEL, RECORD_MODEL, TONE_MODEL

T = TypeVar("T", bound=BaseModel)
log = logging.getLogger("uvicorn.error")

# ADR-006: the note and summary run on Opus 5.5 and favour quality over speed. ADR-011: explain-back runs on the
# live model, Sonnet 5.5, because the patient and physician wait for it. MDD-005: the trust advisor (nudges and
# culture cues) runs in the background on the tone model, never on the turn's critical path.
RECORD_PURPOSES = frozenset({"clinical_note", "patient_summary"})
DEFAULT_MODELS_BY_PURPOSE: dict[str, str] = {
    "tone_check": TONE_MODEL,
    "name_extract": TONE_MODEL,
    "trust": TONE_MODEL,
    "explain_back": LIVE_MODEL,
    **{purpose: RECORD_MODEL for purpose in RECORD_PURPOSES},
}
# A live call that hangs would hold the visit: after this long the SDK gives up, and the turn ends as `failed`
# (CDR-001) instead of leaving everyone waiting. Two retries cover a transient error or an overloaded response.
LIVE_TIMEOUT_S = 25.0
MAX_RETRIES = 2
# Record calls think harder and write longer than a live turn; live calls keep the low-latency settings.
RECORD_EFFORT = "high"
RECORD_MAX_TOKENS = 16000
LIVE_MAX_TOKENS = 4096

# Models with no server-side fallback: they take the plain request, without the fallback beta.
WITHOUT_SERVER_FALLBACK = frozenset({TONE_MODEL})


class ModelRefused(Exception):
    pass


class Model(Protocol):
    async def parse(self, *, purpose: str, system: str, user: str, schema: type[T]) -> T: ...


class ClaudeModel:
    def __init__(
        self,
        model_id: str = LIVE_MODEL,
        client: Any | None = None,
        effort: str = "low",
        models_by_purpose: dict[str, str] | None = None,
    ) -> None:
        self.model_id = model_id
        self.client = client or anthropic.AsyncAnthropic(timeout=LIVE_TIMEOUT_S, max_retries=MAX_RETRIES)
        # Live turns favour latency (under 3 seconds); tune with the tone set (EDR-002).
        self.effort = effort
        # ADR-006 amended 2026-10-25: the tone check runs on Haiku; the note and summary on Opus (ADR-006);
        # every other call on model_id.
        self.models_by_purpose = dict(DEFAULT_MODELS_BY_PURPOSE) if models_by_purpose is None else models_by_purpose

    async def parse(self, *, purpose: str, system: str, user: str, schema: type[T]) -> T:
        model = self.models_by_purpose.get(purpose, self.model_id)
        record = purpose in RECORD_PURPOSES
        request: dict[str, Any] = {
            "model": model,
            "max_tokens": RECORD_MAX_TOKENS if record else LIVE_MAX_TOKENS,
            "system": system,
            "output_config": {"effort": RECORD_EFFORT if record else self.effort},
            "messages": [{"role": "user", "content": user}],
            "output_format": schema,
        }
        started = time.perf_counter()
        if model in WITHOUT_SERVER_FALLBACK:
            response = await self.client.messages.parse(**request)
        else:
            # Server-side refusal fallback: a declined request is retried on Anthropic's
            # recommended fallback model inside the same call.
            response = await self.client.beta.messages.parse(
                **request, betas=["server-side-fallback-2026-07-01"], fallbacks="default"
            )
        usage = getattr(response, "usage", None)
        log.info(
            "model %s %s %.2fs, %s output tokens",
            purpose,
            model,
            time.perf_counter() - started,
            getattr(usage, "output_tokens", "?"),
        )
        if response.stop_reason == "refusal" or response.parsed_output is None:
            raise ModelRefused(f"{purpose}: stop_reason={response.stop_reason}")
        return response.parsed_output


Handler = Callable[[str], BaseModel]


class ScriptedModel:
    """Deterministic model for tests and keyless runs: one handler per purpose (EDR-002)."""

    def __init__(self, handlers: dict[str, Handler]) -> None:
        self.handlers = handlers
        self.calls: list[tuple[str, str]] = []

    async def parse(self, *, purpose: str, system: str, user: str, schema: type[T]) -> T:
        self.calls.append((purpose, user))
        result = self.handlers[purpose](user)
        assert isinstance(result, schema), f"{purpose} handler returned {type(result).__name__}"
        return result
