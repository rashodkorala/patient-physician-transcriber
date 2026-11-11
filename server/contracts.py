"""Wire contracts for the visit channel and translated turns.

@implements CDR-001: Visit WebSocket event contract
@implements CDR-002: Turn result schema
@implements CDR-003: Participant names and interpreter lines on the visit channel
@implements CDR-004: Interpreter voice playback on the visit channel
@implements ADR-003: Human interpreter escalation on low confidence and high-risk moments
@implements TDM-002: Presenter mismatch control for the blocked-dose beat
@implements CDR-005: Consent and explain-back on the visit channel
@implements CDR-006: Record chain entries, review corrections, interpreter dismissal, and presenter controls
@implements CDR-007: Clinical note with provenance and patient summary on the visit channel
@implements TDM-005: Hidden record-tamper control for the demo
@implements CDR-008: Patient signals, manner, trust updates, companion turns, and the closing check on the visit channel
@implements IDR-005: Manner vocabulary and voice delivery
@contract ws:/ws/visit
@contract TurnResult
@contract TurnCaption
@see openspec/tdr/cdr/cdr-008-patient-voice-manner-and-trust-events.md
@see openspec/tdr/cdr/cdr-001-visit-websocket-events.md
@see openspec/tdr/cdr/cdr-002-turn-result-schema.md
@see openspec/tdr/cdr/cdr-003-names-and-interpreter-lines.md
@see openspec/tdr/cdr/cdr-004-interpreter-voice-playback-events.md
@see openspec/tdr/cdr/cdr-005-consent-and-explain-back-events.md
@see openspec/tdr/cdr/cdr-006-record-entries-review-corrections-and-tamper.md
@see openspec/tdr/cdr/cdr-007-clinical-note-and-patient-summary.md
@see openspec/tdr/tdm/tdm-005-hidden-record-tamper-control.md
"""

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

if TYPE_CHECKING:  # the chains import this module, so their result types are named for type checking only
    from chains import explain_back as eb
    from chains import note as nt
    from chains import summary as sm

Language = Literal["pa-IN", "fr-CA", "en-CA", "si-LK", "ta-LK"]
PatientLanguage = Literal["pa-IN", "fr-CA", "si-LK", "ta-LK"]
# TDM-003: patient languages the server accepts only in test mode, never on stage.
# Selectable only in test mode (TDM-003). Tamil left test mode on 6 November 2026 (TDM-004).
TEST_LANGUAGES: tuple[PatientLanguage, ...] = ("si-LK",)
Speaker = Literal["patient", "physician", "companion"]
ToneTag = Literal["reassuring", "respectful", "empathetic", "neutral", "urgent", "uncertain"]
ToneLabel = Literal["respectful", "reassuring", "empathetic", "neutral"]
Emotion = Literal["calm", "worried", "embarrassed", "in_pain", "relieved", "confused"]
# IDR-005: how a turn was said, read from the words; plain is the default.
Manner = Literal["plain", "warm", "reassuring", "gentle", "serious", "urgent", "apologetic", "encouraging"]
# CDR-008: the patient's own signals during the visit.
PatientSignal = Literal["not_understood", "slower", "repeat"]
TrustCueKind = Literal["reassurance", "understanding", "culture"]
Certainty = Literal["high", "medium", "low"]
CriticalKind = Literal["dose", "unit", "frequency", "date", "number", "medication"]
TurnStatusValue = Literal["final", "readback_required", "blocked", "escalated"]
CaptionStatus = Literal["final", "blocked", "escalated"]
Role = Literal["controller", "screen", "review"]
IntroductionState = Literal["pending", "asking_physician", "asking_patient", "done", "skipped"]
NameRole = Literal["physician", "patient"]
LinePurpose = Literal[
    "introduction",
    "ask_physician_name",
    "ask_patient_name",
    "welcome",
    # CDR-008: the interpreter relays a patient signal to the physician, and asks the patient if anything is unclear.
    "signal_not_understood",
    "signal_slower",
    "ask_if_clear",
]
MANNERS: tuple[Manner, ...] = (
    "plain",
    "warm",
    "reassuring",
    "gentle",
    "serious",
    "urgent",
    "apologetic",
    "encouraging",
)
PATIENT_SIGNALS: tuple[PatientSignal, ...] = ("not_understood", "slower", "repeat")
NAME_MAX = 60
SPEECH_ID_MAX = 64

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
    # IDR-005: how the speaker said it, read from the words. Every turn has one; plain when nothing is marked.
    manner: Manner = "plain"


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
    # CDR-008: the physician's manner on a final physician turn only; null for every patient or companion turn.
    manner: Manner | None = None

    @model_validator(mode="after")
    def _manner_only_for_physician(self) -> "TurnCaption":
        if self.manner is not None and (self.speaker != "physician" or self.status != "final"):
            raise ValueError("manner is public only on a final physician turn (CDR-008)")
        return self


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
        manner=result.manner if result.speaker == "physician" else None,
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


EscalationReason = Literal["low_confidence", "tone_failure", "high_risk", "requested"]


class InterpreterEscalation(Wire):
    """interpreter.escalation, every role: a human interpreter offered (or, with "requested", asked for)."""

    reason: EscalationReason
    turn_id: str | None = None


class SegmentAmended(Wire):
    """segment.amended, every role: a correction applied or a confirmation recorded (CDR-001, extended by CDR-006).

    For `amend`, newText, amendmentId, translation, and entryId are set; for `confirm`, version and entryId.
    """

    segment_id: str
    by: Literal["patient", "physician"]
    action: Literal["confirm", "amend"]
    new_text: str | None = None
    # CDR-006: optional, so a client built before review corrections ignores them.
    amendment_id: str | None = None
    version: str | None = None
    translation: str | None = None
    tone_label: ToneLabel | None = None
    critical_values: list[CaptionCriticalValue] | None = None
    entry_id: str | None = None


class RecordIntegrity(Wire):
    status: Literal["verified", "broken"]
    head_hash: str
    broken_at: str | None = None


class DemoInjectionState(Wire):
    """demo.injection_state, controller only (TDM-002): the presenter's mismatch injection."""

    state: Literal["armed", "fired", "cancelled"]


class ErrorPayload(Wire):
    message: str
    command: str | None = None


# ---------- CDR-004 ----------


class VoicePlayback(Wire):
    """Payload of voice.started and voice.ended, controller only: what the interpreter's voice began or stopped playing."""

    speech_id: str = Field(min_length=1, max_length=SPEECH_ID_MAX)
    language: Language


class VoiceSpeaking(Wire):
    """voice.speaking, and visit.state.speaking: whether the interpreter's voice is playing, for every role.

    Carries no text, tone, emotion, or certainty; the id and language are set exactly when speaking.
    """

    speaking: bool
    speech_id: str | None = None
    language: Language | None = None

    @model_validator(mode="after")
    def _set_when_speaking(self) -> "VoiceSpeaking":
        if self.speaking != (self.speech_id is not None and self.language is not None):
            raise ValueError("speechId and language are set exactly when speaking")
        if not self.speaking and (self.speech_id is not None or self.language is not None):
            raise ValueError("speechId and language are null when not speaking")
        return self


SILENT = VoiceSpeaking(speaking=False)


class LineText(Wire):
    language: Language
    text: str


# ---------- CDR-005: consent (the explain-back half is built separately) ----------

ConsentBy = Literal["patient", "physician_on_behalf"]
REASON_MAX = 200


class ConsentNotice(Wire):
    """The reviewed notice for the visit's patient language; lines hold the patient language first, English second."""

    notice_id: str
    speech_id: str
    version: str
    language: PatientLanguage
    lines: list[LineText]


class ConsentSpeak(Wire):
    """consent.speak, controller only: play the notice now, by its speech id."""

    speech_id: str
    language: PatientLanguage


class ConsentGive(Wire):
    notice_version: str
    language: PatientLanguage


class ConsentWithdraw(Wire):
    reason: str | None = Field(default=None, max_length=REASON_MAX)


class ConsentState(Wire):
    """consent.changed, and visit.state.consentState: the latest consent change, with its chain entry id."""

    state: Literal["given", "withdrawn"]
    at: str
    by: ConsentBy
    notice_id: str
    notice_version: str
    language: PatientLanguage
    entry_id: str


RefusedReason = Literal[
    "consent_required",
    "consent_already_given",
    "consent_not_given",
    "wrong_notice",
    "wrong_language",
    "not_allowed",
    "not_found",
    "not_current",
    "busy",
    "invalid",
]


class CommandRefused(Wire):
    """command.refused, only to the review connection that sent the command; no free text, so nothing can leak."""

    command: str
    reason: RefusedReason


# ---------- CDR-006: record chain entries and interpreter dismissal ----------

EntryKind = Literal["turn", "consent", "amendment", "confirmation", "explain_back", "interpreter", "summary", "signal"]
EscalationAction = Literal["offer", "request", "mark", "dismiss"]
DismissReason = Literal["declined", "resolved", "simulated_call_ended"]
EscalationEntryReason = Literal[
    "low_confidence", "tone_failure", "high_risk", "requested", "declined", "resolved", "simulated_call_ended"
]


class RecordEntry(Wire):
    """The payload of one hash chain entry (IDR-003): typed, and named by entryId (a turn's is its turnId)."""

    entry_id: str
    kind: EntryKind
    at: str
    body: dict


class TurnEntryBody(TurnCaption):
    """A settled turn as chained: the public caption only, never a private field or an unspoken translation."""

    settled_as: CaptionStatus
    physician_name: str | None = None
    patient_name: str | None = None


class ConsentEntryBody(Wire):
    """A consent change as chained: ConsentState without entryId, plus the SHA-256 of the notice as shown."""

    state: Literal["given", "withdrawn"]
    at: str
    by: ConsentBy
    notice_id: str
    notice_version: str
    language: PatientLanguage
    notice_sha256: str
    reason: str | None = None


class EscalationEntry(Wire):
    """An interpreter offer, request, high-risk mark, or dismissal, as recorded in the transcript (ADR-003)."""

    entry_id: str
    action: EscalationAction
    reason: EscalationEntryReason
    at: str
    turn_id: str | None = None
    note: str | None = None


class InterpreterDismiss(Wire):
    reason: DismissReason


class InterpreterDismissed(Wire):
    """interpreter.dismissed, every role: the controller ended the offer or request, so every screen clears it."""

    reason: DismissReason
    at: str
    entry_id: str


class InjectionStatus(Wire):
    """visit.state.injection, controller only (TDM-002): armed or idle, and the turns the mismatch fired on."""

    state: Literal["idle", "armed"]
    injected_turn_ids: list[str]


# ---------- CDR-006: review corrections, confirmations, and the tamper control ----------

SegmentStage = Literal["translating", "verifying", "retrying", "applied", "refused"]
SEGMENT_TEXT_MAX = 1000
# A segment's version: "original", or the amendmentId of an applied correction.
ORIGINAL = "original"


class AmendmentEntryBody(Wire):
    """An applied correction as chained: it points at the turn entry and never edits it."""

    segment_id: str
    amendment_id: str
    replaces: str  # "original" or the amendmentId it replaces
    source_text: str
    translation: str
    tone_label: ToneLabel
    critical_values: list[CaptionCriticalValue]
    by: Literal["patient"] = "patient"


class ConfirmationEntryBody(Wire):
    """A confirmation as chained: the version of the segment the patient confirmed."""

    segment_id: str
    version: str
    by: Literal["patient"] = "patient"


class SegmentConfirm(Wire):
    """segment.confirm, review only: confirm the named version, which must still be current."""

    segment_id: str
    version: str


class SegmentAmend(Wire):
    """segment.amend, review only: the recognised text of the patient re-speaking one of their own turns."""

    segment_id: str
    text: str = Field(min_length=1, max_length=SEGMENT_TEXT_MAX)
    language: PatientLanguage
    recognition_confidence: float = Field(ge=0, le=1)


class SegmentStatus(Wire):
    """segment.status, every role: one stage of a correction, or its outcome; never any text."""

    segment_id: str
    amendment_id: str
    stage: SegmentStage
    reason: Literal["blocked", "escalated", "failed"] | None = None


class SegmentAnalysis(Wire):
    """segment.analysis, controller only: a correction's full turn graph result."""

    segment_id: str
    amendment_id: str
    result: TurnResult


class SegmentAmendment(Wire):
    """One applied correction in a segment's history, as every role sees it."""

    amendment_id: str
    source_text: str
    translation: str
    tone_label: ToneLabel
    critical_values: list[CaptionCriticalValue]
    at: str
    entry_id: str


class SegmentAmendmentWithAnalysis(SegmentAmendment):
    """One applied correction with its full turn graph result: controller only."""

    analysis: TurnResult


class SegmentConfirmation(Wire):
    version: str
    at: str
    entry_id: str


class SegmentHistory(Wire):
    """visit.state.segments, every role: a turn with a confirmation or a correction, original first."""

    segment_id: str
    original: TurnCaption
    amendments: list[SegmentAmendment]
    confirmed: SegmentConfirmation | None
    current: str  # "original" or the latest amendmentId


class SegmentHistoryController(SegmentHistory):
    """visit.state.segments for the controller: each amendment carries its analysis."""

    amendments: list[SegmentAmendmentWithAnalysis]  # type: ignore[assignment]


class TamperRecord(Wire):
    """demo.tamper_record, controller only (TDM-005): alter one turn or amendment entry, once per visit."""

    entry_id: str


class TamperState(Wire):
    """demo.tamper_state, and visit.state.tamper, controller only (TDM-005): the entry the control altered."""

    entry_id: str
    at: str


# ---------- CDR-005: explain-back ----------

ExplainBackStateValue = Literal["listening", "checking", "done", "failed", "cancelled"]
ExplainBackOutcome = Literal["matched", "missed", "contradicted"]
ExplainBackKind = Literal["dose", "frequency", "medication", "number", "date", "instruction", "warning", "follow_up"]


class ExplainBackRef(Wire):
    """explainback.check and explainback.cancel, controller only."""

    explain_back_id: str


class ExplainBackState(Wire):
    """explainback.state, and visit.state.explainBack, every role: no text, items, or outcomes."""

    explain_back_id: str
    state: ExplainBackStateValue
    explanation_turn_ids: list[str]


class ExplainBackItem(Wire):
    item_id: str
    kind: ExplainBackKind
    instruction: str
    source_turn_ids: list[str]
    outcome: ExplainBackOutcome
    decided_by: Literal["code", "model"]
    expected: str | None = None
    heard: str | None = None
    evidence_turn_ids: list[str]


class ExplainBackResultBody(Wire):
    """An explain-back result as chained: ExplainBackResult without entryId."""

    explain_back_id: str
    plan_head_hash: str
    explanation_turn_ids: list[str]
    items: list[ExplainBackItem]


class ExplainBackResult(ExplainBackResultBody):
    """explainback.result, and visit.state.explainBackResults, controller only."""

    entry_id: str


def wire_explain_back(result: "eb.ExplainBackResult") -> ExplainBackResult:
    """The chain's result as sent, field for field; the internal attempt count is not on the wire."""
    return ExplainBackResult(
        explain_back_id=result.explain_back_id,
        plan_head_hash=result.plan_head_hash,
        explanation_turn_ids=list(result.explanation_turn_ids),
        items=[
            ExplainBackItem(
                item_id=i.item_id,
                kind=i.kind,
                instruction=i.instruction,
                source_turn_ids=list(i.source_turn_ids),
                outcome=i.outcome,
                decided_by=i.decided_by,
                expected=i.expected,
                heard=i.heard,
                evidence_turn_ids=list(i.evidence_turn_ids),
            )
            for i in result.items
        ],
        entry_id=result.entry_id,
    )


# ---------- CDR-007: clinical note and patient summary ----------

ArtefactKind = Literal["note", "summary"]
ArtefactStage = Literal["generating", "checking", "retrying", "ready", "failed", "refused"]
ProvenanceTag = Literal["patient_stated", "physician_stated", "companion_stated", "interpreter_stated", "ai_inference"]
NoteHeading = Literal["Presenting complaint", "History", "Assessment", "Plan", "Follow-up"]


class ArtefactStatus(Wire):
    """note.status (controller only) and summary.status (every role); detail is for controllers only."""

    artefact_id: str
    kind: ArtefactKind
    stage: ArtefactStage
    detail: str | None = None


class SourceRef(Wire):
    """A cited source: a turn at its frozen effective version, or an interpreter line ("original")."""

    kind: Literal["turn", "interpreter_line"]
    id: str
    version: str


class NoteSentence(Wire):
    sentence_id: str
    text: str
    tag: ProvenanceTag
    sources: list[SourceRef] = Field(min_length=1)


class NoteSection(Wire):
    heading: NoteHeading
    sentences: list[NoteSentence]


class TagDowngrade(Wire):
    """A sentence whose stated tag code changed to ai_inference; `from_` is `from` on the wire."""

    sentence_id: str
    from_: ProvenanceTag = Field(alias="from")
    to: Literal["ai_inference"] = "ai_inference"


class ClinicalNote(Wire):
    """note.ready, and visit.state.note, controller only: a checked draft the physician remains author of."""

    note_id: str
    language: Literal["en-CA"]
    based_on_head: str
    generated_at: str
    sections: list[NoteSection]
    untranslated_turn_ids: list[str]
    tag_downgrades: list[TagDowngrade]


class SummarySentence(Wire):
    """One summary sentence; its sentenceId is also its speech id, `{summaryId}.{index}`."""

    sentence_id: str
    index: int = Field(ge=0)
    text: str
    sources: list[SourceRef]


class SummaryValue(Wire):
    kind: CriticalKind
    text: str
    source_turn_id: str


class PatientSummary(Wire):
    """summary.ready, and visit.state.summary, every role: only ever a summary that passed its value check."""

    summary_id: str
    language: PatientLanguage
    based_on_head: str
    generated_at: str
    sentences: list[SummarySentence]
    values: list[SummaryValue]
    check: Literal["passed"] = "passed"


class SummaryMismatch(Wire):
    kind: CriticalKind
    expected: str
    found: str | None
    source_turn_id: str | None
    problem: Literal["changed", "missing", "unsupported"]


class SummaryCheck(Wire):
    """summary.check, and visit.state.summaryChecks, controller only: every check outcome and the values compared."""

    summary_id: str
    attempt: Literal[1, 2]
    outcome: Literal["passed", "failed"]
    mismatches: list[SummaryMismatch]


class SummaryRef(Wire):
    """summary.read_aloud and summary.stop, from review or the controller."""

    summary_id: str


class SummarySpeak(Wire):
    """summary.speak, controller only: play the named sentence ids in order, or stop."""

    summary_id: str
    action: Literal["play", "stop"]
    speech_ids: list[str]


class ArtefactsStale(Wire):
    """artefacts.stale, every role: the chain grew after the current note or summary; note is false for screens."""

    note: bool
    summary: bool
    head_hash: str


def _refs(refs) -> list[SourceRef]:
    return [SourceRef(kind=r.kind, id=r.id, version=r.version) for r in refs]


def wire_note(note: "nt.ClinicalNote") -> ClinicalNote:
    """The chain's note as sent, field for field; TagDowngrade.from_ goes out as `from`, attempts stays internal."""
    return ClinicalNote(
        note_id=note.note_id,
        language=note.language,
        based_on_head=note.based_on_head,
        generated_at=note.generated_at,
        sections=[
            NoteSection(
                heading=section.heading,
                sentences=[
                    NoteSentence(sentence_id=s.sentence_id, text=s.text, tag=s.tag, sources=_refs(s.sources))
                    for s in section.sentences
                ],
            )
            for section in note.sections
        ],
        untranslated_turn_ids=list(note.untranslated_turn_ids),
        tag_downgrades=[TagDowngrade(sentence_id=d.sentence_id, from_=d.from_, to=d.to) for d in note.tag_downgrades],
    )


def wire_summary(summary: "sm.PatientSummary") -> PatientSummary:
    """The chain's passed summary as sent, field for field."""
    return PatientSummary(
        summary_id=summary.summary_id,
        language=summary.language,  # type: ignore[arg-type]
        based_on_head=summary.based_on_head,
        generated_at=summary.generated_at,
        sentences=[
            SummarySentence(sentence_id=s.sentence_id, index=s.index, text=s.text, sources=_refs(s.sources))
            for s in summary.sentences
        ],
        values=[
            SummaryValue(kind=v.kind, text=v.text, source_turn_id=v.source_turn_id)  # type: ignore[arg-type]
            for v in summary.values
        ],
        check=summary.check,
    )


def wire_summary_check(check: "sm.SummaryCheck") -> SummaryCheck:
    """The chain's check as sent; its internal `problems` reach controllers only through ArtefactStatus.detail."""
    return SummaryCheck(
        summary_id=check.summary_id,
        attempt=check.attempt,  # type: ignore[arg-type]
        outcome=check.outcome,
        mismatches=[
            SummaryMismatch(
                kind=m.kind,  # type: ignore[arg-type]
                expected=m.expected,
                found=m.found,
                source_turn_id=m.source_turn_id,
                problem=m.problem,
            )
            for m in check.mismatches
        ],
    )


# ---------- CDR-008: patient signals and trust updates ----------


class PatientSignalCommand(Wire):
    """patient.signal, from the patient's device (review role) only."""

    signal: PatientSignal


class PatientSignalEntry(Wire):
    """patient.signal to every role, and the body of a `signal` chain entry (its entryId is the signalId)."""

    signal_id: str
    signal: PatientSignal
    after_turn_id: str | None
    at: str


TRUST_CUE_MAX = 200


class TrustCue(Wire):
    """A short English suggestion for the physician only; never chained, never sent to the note or summary."""

    kind: TrustCueKind
    text: str = Field(min_length=1, max_length=TRUST_CUE_MAX)


class TrustUpdate(Wire):
    """trust.update, controller only: one per settled final turn, and one per accepted patient signal."""

    turn_id: str | None
    speaker: Speaker | None
    emotion: Emotion | None
    manner: Manner | None
    reassurance_landed: bool | None
    signal: PatientSignal | None
    cue: TrustCue | None
    at: str

    @model_validator(mode="after")
    def _one_kind(self) -> "TrustUpdate":
        if self.signal is not None:
            if self.speaker is not None or self.emotion is not None or self.manner is not None:
                raise ValueError("a signal update carries no speaker, emotion, or manner (CDR-008)")
            if self.reassurance_landed is not None:
                raise ValueError("a signal update carries no reassurance mark (CDR-008)")
        else:
            if self.turn_id is None or self.speaker is None or self.manner is None:
                raise ValueError("a turn update names its turn, speaker, and manner (CDR-008)")
            if (self.speaker == "physician") != (self.emotion is None):
                raise ValueError("emotion is set for patient and companion turns only (CDR-008)")
        return self


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
    # CDR-004: optional, so a client built before voice playback ignores it.
    speaking: VoiceSpeaking | None = None
    # CDR-005: optional, so a client built before consent ignores them.
    consent_notice: ConsentNotice | None = None
    consent_state: ConsentState | None = None
    # CDR-006: optional; injection and escalations are controller only.
    interpreter_open: bool = False
    injection: InjectionStatus | None = None
    escalations: list[EscalationEntry] = Field(default_factory=list)
    segments: list[SegmentHistoryController] = Field(default_factory=list)
    tamper: TamperState | None = None
    # CDR-005 explain-back: the latest one's state for every role; the results are controller only.
    explain_back: ExplainBackState | None = None
    explain_back_results: list[ExplainBackResult] = Field(default_factory=list)
    # CDR-007: the note and every summary check are controller only; only a passed summary is ever held.
    note: ClinicalNote | None = None
    note_stale: bool = False
    summary_checks: list[SummaryCheck] = Field(default_factory=list)
    summary: PatientSummary | None = None
    summary_stale: bool = False
    # CDR-008: the patient's signals for every role; the trust timeline for the controller only.
    signals: list[PatientSignalEntry] = Field(default_factory=list)
    trust: list[TrustUpdate] = Field(default_factory=list)


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
    # CDR-004: optional, so a client built before voice playback ignores it.
    speaking: VoiceSpeaking | None = None
    # CDR-005: optional, so a client built before consent ignores them.
    consent_notice: ConsentNotice | None = None
    consent_state: ConsentState | None = None
    # CDR-006: optional, for every role.
    interpreter_open: bool = False
    segments: list[SegmentHistory] = Field(default_factory=list)
    # CDR-005: the latest explain-back's state only, never its result.
    explain_back: ExplainBackState | None = None
    # CDR-007: only a summary that passed its value check.
    summary: PatientSummary | None = None
    summary_stale: bool = False
    # CDR-008: the patient's signals; never the trust timeline.
    signals: list[PatientSignalEntry] = Field(default_factory=list)


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
        "consent.speak",
        "error",
        # CDR-005, CDR-006, TDM-005, and CDR-007.
        "explainback.result",
        "segment.analysis",
        "demo.tamper_state",
        "note.status",
        "note.ready",
        "summary.check",
        "summary.speak",
        # CDR-008.
        "trust.update",
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
        "voice.started",
        "voice.ended",
        "visit.mark_high_risk",
        "demo.inject_mismatch",
        "demo.cancel_injection",
        "interpreter.dismiss",
        # CDR-005, TDM-005, and CDR-007.
        "explainback.start",
        "explainback.check",
        "explainback.cancel",
        "demo.tamper_record",
        "note.generate",
        "summary.generate",
        # CDR-008.
        "visit.ask_if_clear",
    }
)

# CDR-005: commands the patient's review screen or the controller may send; a screen's copy is dropped.
# CDR-007 adds the summary's read-aloud and stop.
REVIEW_OR_CONTROLLER_COMMANDS = frozenset(
    {"consent.give", "consent.withdraw", "consent.read_aloud", "summary.read_aloud", "summary.stop"}
)

# CDR-006: commands only the patient's review screen may send; a controller copy is refused with `error`,
# and a screen copy is refused silently (a screen never receives `error` or `command.refused`).
REVIEW_COMMANDS = frozenset({"segment.confirm", "segment.amend", "patient.signal"})

# CDR-007: events whose payload differs by role. summary.status loses `detail`, and artefacts.stale always says
# `note: false`, for screen and review connections.
ROLE_SHAPED_EVENTS = frozenset({"summary.status", "artefacts.stale"})
