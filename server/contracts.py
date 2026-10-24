"""Wire contracts for the visit channel and translated turns.

@implements CDR-001: Visit WebSocket event contract
@implements CDR-002: Turn result schema
@contract ws:/ws/visit
@contract TurnResult
@contract TurnCaption
@see openspec/tdr/cdr/cdr-001-visit-websocket-events.md
@see openspec/tdr/cdr/cdr-002-turn-result-schema.md
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

Language = Literal["pa-IN", "fr-CA", "en-CA"]
PatientLanguage = Literal["pa-IN", "fr-CA"]
Speaker = Literal["patient", "physician", "companion"]
ToneTag = Literal["reassuring", "respectful", "empathetic", "neutral", "urgent", "uncertain"]
ToneLabel = Literal["respectful", "reassuring", "empathetic", "neutral"]
Emotion = Literal["calm", "worried", "embarrassed", "in_pain", "relieved", "confused"]
Certainty = Literal["high", "medium", "low"]
CriticalKind = Literal["dose", "unit", "frequency", "date", "number", "medication"]
TurnStatusValue = Literal["final", "readback_required", "blocked", "escalated"]
CaptionStatus = Literal["final", "blocked", "escalated"]
Role = Literal["controller", "screen", "review"]

TONE_LABELS: tuple[ToneLabel, ...] = ("respectful", "reassuring", "empathetic", "neutral")


class Wire(BaseModel):
    """camelCase on the wire, snake_case in Python."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    def wire(self) -> dict:
        return self.model_dump(by_alias=True, mode="json")


# ---------- CDR-002 ----------


class GlossaryEntry(Wire):
    term: str
    translation: str
    explanation: str


class CriticalValue(Wire):
    kind: CriticalKind
    source: str
    translated: str
    matched: bool


class CaptionCriticalValue(Wire):
    kind: str
    source: str
    translated: str


class TurnResult(Wire):
    """Full turn; server and physician controller only (via turn.analysis)."""

    turn_id: str
    speaker: Speaker
    source_language: Language
    target_language: Language
    source_text: str
    translation: str
    back_translation: str
    tone_tags: list[ToneTag]
    emotion: Emotion
    certainty: Certainty
    glossary_used: list[GlossaryEntry]
    critical_values: list[CriticalValue]
    confidence: float
    status: TurnStatusValue
    attempts: int


class TurnCaption(Wire):
    """Public projection; every screen (via turn.result). Never carries private fields."""

    turn_id: str
    speaker: Speaker
    source_language: Language
    target_language: Language
    source_text: str
    status: CaptionStatus
    translation: str | None
    tone_label: ToneLabel | None
    glossary_used: list[GlossaryEntry]
    critical_values: list[CaptionCriticalValue]
    readback_confirmed: bool


def to_caption(result: TurnResult, readback_confirmed: bool = False) -> TurnCaption:
    """Project a settled turn for shared screens.

    Blocked and escalated turns never expose their translation, tone, or translated values.
    Callers emit a caption only once a turn is spoken, blocked, or escalated (CDR-002).
    """
    if result.status in ("blocked", "escalated"):
        return TurnCaption(
            turn_id=result.turn_id,
            speaker=result.speaker,
            source_language=result.source_language,
            target_language=result.target_language,
            source_text=result.source_text,
            status=result.status,
            translation=None,
            tone_label=None,
            glossary_used=[],
            critical_values=[],
            readback_confirmed=False,
        )
    tone: ToneLabel = next((t for t in result.tone_tags if t in TONE_LABELS), "neutral")  # type: ignore[assignment]
    return TurnCaption(
        turn_id=result.turn_id,
        speaker=result.speaker,
        source_language=result.source_language,
        target_language=result.target_language,
        source_text=result.source_text,
        status="final",
        translation=result.translation,
        tone_label=tone,
        glossary_used=result.glossary_used,
        critical_values=[
            CaptionCriticalValue(kind=v.kind, source=v.source, translated=v.translated) for v in result.critical_values
        ],
        readback_confirmed=readback_confirmed,
    )


# ---------- CDR-001 payloads ----------


class TurnStarted(Wire):
    turn_id: str
    speaker: Speaker
    language: Language


class TurnStatus(Wire):
    turn_id: str
    stage: str


class EmpathyNudge(Wire):
    turn_id: str
    emotion: Emotion
    suggestion: str
    phrase: str
    phrase_language: Language


class InterpreterEscalation(Wire):
    reason: Literal["low_confidence", "tone_failure", "high_risk", "requested"]
    turn_id: str | None = None


class SegmentAmended(Wire):
    segment_id: str
    by: Literal["patient", "physician"]
    action: Literal["confirm", "amend"]
    new_text: str | None = None


class RecordIntegrity(Wire):
    status: Literal["verified", "broken"]
    head_hash: str
    broken_at: str | None = None


class DemoInjectionState(Wire):
    state: Literal["armed", "fired", "cancelled"]


class ErrorPayload(Wire):
    message: str
    command: str | None = None


class CurrentTurnPublic(Wire):
    turn_id: str
    speaker: Speaker
    source_text: str
    stage: str


class VisitStateController(Wire):
    patient_language: PatientLanguage
    physician_language: Language
    consent: str | None
    paused: bool
    turns: list[TurnResult]
    current_turn: TurnResult | None = None
    pending_readback: str | None = None
    nudges: list[EmpathyNudge]
    integrity: RecordIntegrity


class VisitStatePublic(Wire):
    patient_language: PatientLanguage
    physician_language: Language
    consent: str | None
    paused: bool
    turns: list[TurnCaption]
    current_turn: CurrentTurnPublic | None = None
    integrity: RecordIntegrity


# ---------- CDR-001 commands ----------


class SetLanguages(Wire):
    patient_language: PatientLanguage
    physician_language: Literal["en-CA"]


class TurnSubmit(Wire):
    speaker: Speaker
    language: Language
    text: str
    recognition_confidence: float


class TurnRef(Wire):
    """Payload of turn.readback_confirm and turn.readback_reject, and of turn.readback_required."""

    turn_id: str


class MarkHighRisk(Wire):
    turn_id: str | None = None
    note: str | None = None


class Envelope(Wire):
    type: str
    visit_id: str
    seq: int
    ts: str
    payload: dict


# Events the server never sends to screen or review connections (CDR-001).
CONTROLLER_ONLY_EVENTS = frozenset(
    {"turn.analysis", "turn.readback_required", "empathy.nudge", "demo.injection_state", "error"}
)

# Commands only the controller may send (CDR-001).
CONTROLLER_COMMANDS = frozenset(
    {
        "visit.set_languages",
        "turn.submit",
        "turn.readback_confirm",
        "turn.readback_reject",
        "visit.mark_high_risk",
        "demo.inject_mismatch",
        "demo.cancel_injection",
    }
)
