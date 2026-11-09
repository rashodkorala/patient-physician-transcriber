"""Record chain payloads (CDR-006) for the grounded generation tests (ADR-011), built the way the server builds them.

Critical values come from critical_values.check, as the turn graph computes them for a faithful translation.
"""

import asyncio
from collections.abc import Callable

from pydantic import BaseModel

import critical_values
from contracts import InterpreterLine, LineText
from llm import ScriptedModel

HEAD = "a" * 64
SECRETS = ("BACKTRANSLATION-SECRET", "worried", "BLOCKED-SECRET", "ESCALATED-SECRET", "NUDGE-SECRET", "TAMPERED")


def turn_entry(
    turn_id: str,
    speaker: str,
    source_language: str,
    source_text: str,
    target_language: str,
    translation: str,
    *,
    medications: dict[str, list[str]] | None = None,
    settled: str = "final",
    readback: bool = False,
    name: str | None = None,
) -> dict:
    medications = medications or {}
    values = critical_values.check(
        source_text, source_language, translation, target_language, source_text, list(medications), medications
    )
    body = {
        "turnId": turn_id,
        "speaker": speaker,
        "sourceLanguage": source_language,
        "targetLanguage": target_language,
        "sourceText": source_text,
        "status": settled,
        "settledAs": settled,
        "translation": translation if settled == "final" else None,
        "toneLabel": "respectful" if settled == "final" else None,
        "glossaryUsed": [],
        "criticalValues": [
            {"kind": v.kind, "source": v.source, "translated": v.translated} for v in values if settled == "final"
        ],
        "readbackConfirmed": readback,
    }
    if name and speaker in ("physician", "patient"):
        body[f"{speaker}Name"] = name
    return {"entryId": turn_id, "kind": "turn", "at": "2026-11-09T10:00:00+00:00", "body": body}


def amendment_entry(segment_id: str, amendment_id: str, source_text: str, translation: str) -> dict:
    return {
        "entryId": amendment_id,
        "kind": "amendment",
        "at": "2026-11-09T10:05:00+00:00",
        "body": {
            "segmentId": segment_id,
            "amendmentId": amendment_id,
            "replaces": "original",
            "sourceText": source_text,
            "translation": translation,
            "toneLabel": "neutral",
            "criticalValues": [],
            "by": "patient",
        },
    }


METFORMIN = {"metformin": ["ਮੈਟਫਾਰਮਿਨ"]}


def punjabi_visit() -> list[dict]:
    """A Punjabi visit: a complaint, a confirmed dose, a follow-up, and one blocked and one escalated turn."""
    blocked = turn_entry(
        "b1",
        "physician",
        "en-CA",
        "Take 0.4 milligrams of nitroglycerin BLOCKED-SECRET.",
        "pa-IN",
        "x",
        settled="blocked",
    )
    blocked["body"]["translation"] = "4 ਮਿਲੀਗ੍ਰਾਮ BLOCKED-SECRET"  # defensive: a stray translation must still never leak
    escalated = turn_entry("e1", "patient", "pa-IN", "ਮੈਨੂੰ ESCALATED-SECRET", "en-CA", "x", settled="escalated")
    confirmed = turn_entry(
        "d1",
        "physician",
        "en-CA",
        "Take metformin 500 milligrams twice a day.",
        "pa-IN",
        "ਡਾਕਟਰ ਥਾਮਸ ਕਹਿ ਰਹੇ ਹਨ ਕਿ ਤੁਸੀਂ ਮੈਟਫਾਰਮਿਨ 500 ਮਿਲੀਗ੍ਰਾਮ ਦਿਨ ਵਿੱਚ ਦੋ ਵਾਰ ਲਓ।",
        medications=METFORMIN,
        readback=True,
        name="Thomas",
    )
    # Fields CDR-006 never chains; if one ever slipped in, the snapshot must still drop it.
    confirmed["body"].update(
        {"emotion": "worried", "certainty": "low", "backTranslation": "BACKTRANSLATION-SECRET", "nudge": "NUDGE-SECRET"}
    )
    return [
        turn_entry(
            "p1", "patient", "pa-IN", "ਮੈਨੂੰ ਸ਼ੂਗਰ ਹੈ ਅਤੇ ਮੈਂ ਬਹੁਤ ਥੱਕਿਆ ਰਹਿੰਦਾ ਹਾਂ।", "en-CA",
            "The patient is saying they have diabetes and feel very tired.", name="Harjit",
        ),
        blocked,
        confirmed,
        escalated,
        turn_entry(
            "d2", "physician", "en-CA", "Come back in 2 weeks.", "pa-IN",
            "ਡਾਕਟਰ ਥਾਮਸ ਕਹਿ ਰਹੇ ਹਨ ਕਿ 2 ਹਫ਼ਤਿਆਂ ਬਾਅਦ ਵਾਪਸ ਆਓ।",
        ),
        {"entryId": "x1", "kind": "explain_back", "at": "2026-11-09T10:06:00+00:00", "body": {"items": ["TAMPERED"]}},
    ]  # fmt: skip


WELCOME = InterpreterLine(
    line_id="line-welcome",
    purpose="welcome",
    lines=[LineText(language="pa-IN", text="ਜੀ ਆਇਆਂ ਨੂੰ।"), LineText(language="en-CA", text="Welcome.")],
)


def scripted(purpose: str, *outputs: BaseModel | Callable[[str], BaseModel]) -> ScriptedModel:
    """A model that returns `outputs` in order for `purpose`, one per call (a callable gets the prompt)."""
    queue = list(outputs)

    def handler(user: str) -> BaseModel:
        out = queue.pop(0) if len(queue) > 1 else queue[0]
        return out(user) if callable(out) and not isinstance(out, BaseModel) else out

    return ScriptedModel({purpose: handler})


def run(coroutine):
    return asyncio.run(coroutine)
