"""Wire contracts for the visit channel and translated turns.

@implements CDR-001: Visit WebSocket event contract
@implements CDR-002: Turn result schema
@implements CDR-003: Participant names and interpreter lines on the visit channel
@contract ws:/ws/visit
@contract TurnResult
@contract TurnCaption
@see openspec/tdr/cdr/cdr-001-visit-websocket-events.md
@see openspec/tdr/cdr/cdr-002-turn-result-schema.md
@see openspec/tdr/cdr/cdr-003-names-and-interpreter-lines.md
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic.alias_generators import to_camel

Language = Literal["pa-IN", "fr-CA", "en-CA", "si-LK", "ta-LK"]
PatientLanguage = Literal["pa-IN", "fr-CA", "si-LK", "ta-LK"]
# TDM-003: patient languages the server accepts only in test mode, never on stage.
# Selectable only in test mode (TDM-003). Tamil left test mode on 6 November 2026 (TDM-004).
TEST_LANGUAGES: tuple[PatientLanguage, ...] = ("si-LK",)
Speaker = Literal["patient", "physician", "companion"]
ToneTag = Literal["reassuring", "respectful", "empathetic", "neutral", "urgent", "uncertain"]
ToneLabel = Literal["respectful", "reassuring", "empathetic", "neutral"]
Emotion = Literal["calm", "worried", "embarrassed", "in_pain", "relieved", "confused"]
Certainty = Literal["high", "medium", "low"]
CriticalKind = Literal["dose", "unit", "frequency", "date", "number", "medication"]
TurnStatusValue = Literal["final", "readback_required", "blocked", "escalated"]
CaptionStatus = Literal["final", "blocked", "escalated"]
Role = Literal["controller", "screen", "review"]
IntroductionState = Literal["pending", "asking_physician", "asking_patient", "done", "skipped"]
NameRole = Literal["physician", "patient"]
LinePurpose = Literal["introduction", "ask_physician_name", "ask_patient_name", "welcome"]
NAME_MAX = 60

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
    # CDR-003: optional, so a client built before names ignores them.
    physician_name: str | None = None
    patient_name: str | None = None
    introduction: IntroductionState = "pending"


class VisitStatePublic(Wire):
    patient_language: PatientLanguage
    physician_language: Language
    consent: str | None
    paused: bool
    turns: list[TurnCaption]
    current_turn: CurrentTurnPublic | None = None
    integrity: RecordIntegrity
    # CDR-003: optional, so a client built before names ignores them.
    physician_name: str | None = None
    patient_name: str | None = None
    introduction: IntroductionState = "pending"


# ---------- CDR-001 commands ----------


class SetLanguages(Wire):
    patient_language: PatientLanguage
    physician_language: Literal["en-CA"]


def clean_name(value: str | None) -> str | None:
    """Trimmed, at most NAME_MAX characters, no digits; blank clears the name (CDR-003).

    Digits are refused so a name can never add a number the critical value check would see.
    """
    if value is None:
        return None
    name = " ".join(value.split())
    if not name:
        return None
    if len(name) > NAME_MAX:
        raise ValueError(f"a name is at most {NAME_MAX} characters")
    if any(c.isdigit() for c in name):
        raise ValueError("a name cannot contain digits")
    return name


class Names(Wire):
    """visit.names, and visit.set_names: a field left out of set_names keeps its current name."""

    physician_name: str | None = None
    patient_name: str | None = None

    @field_validator("physician_name", "patient_name")
    @classmethod
    def _clean(cls, value: str | None) -> str | None:
        return clean_name(value)


class LineText(Wire):
    language: Language
    text: str


class InterpreterLine(Wire):
    """interpreter.line: something the interpreter says itself, in each language it is spoken in (CDR-003)."""

    line_id: str
    purpose: LinePurpose
    lines: list[LineText]


class NameProposed(Wire):
    """visit.name_proposed, controller only: a name heard in a reply, waiting for confirmation."""

    role: NameRole
    name: str


class NameReply(Wire):
    role: NameRole
    text: str


class NameRef(Wire):
    """Payload of visit.name_confirm and visit.name_reject."""

    role: NameRole


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
    {
        "turn.analysis",
        "turn.readback_required",
        "empathy.nudge",
        "demo.injection_state",
        "visit.name_proposed",
        "error",
    }
)

# Commands only the controller may send (CDR-001).
CONTROLLER_COMMANDS = frozenset(
    {
        "visit.set_languages",
        "visit.set_names",
        "visit.start_introduction",
        "visit.name_reply",
        "visit.name_confirm",
        "visit.name_reject",
        "turn.submit",
        "turn.readback_confirm",
        "turn.readback_reject",
        "visit.mark_high_risk",
        "demo.inject_mismatch",
        "demo.cancel_injection",
    }
)
