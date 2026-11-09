"""One in-memory visit and the connections watching it.

@implements ADR-007: In-memory visit state with WebSocket updates; no database for the demo
@implements CDR-001: Visit WebSocket event contract
@implements CDR-003: Participant names and interpreter lines on the visit channel
@implements CDR-004: Interpreter voice playback on the visit channel
@implements ADR-003: Human interpreter escalation on low confidence and high-risk moments
@implements TDM-002: Presenter mismatch control for the blocked-dose beat
@implements CDR-005: Consent and explain-back on the visit channel
@implements CDR-006: Record chain entries, review corrections, interpreter dismissal, and presenter controls
@implements IDR-003: SHA-256 hash chain for the record-verified badge
@contract ws:/ws/visit
@see openspec/tdr/adr/adr-007-in-memory-state-websocket.md
@see openspec/tdr/cdr/cdr-006-record-entries-review-corrections-and-tamper.md
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from contracts import (
    CONTROLLER_ONLY_EVENTS,
    SILENT,
    ConsentNotice,
    ConsentState,
    CurrentTurnPublic,
    EmpathyNudge,
    EntryKind,
    Envelope,
    EscalationEntry,
    InjectionStatus,
    InterpreterLine,
    IntroductionState,
    Names,
    RecordEntry,
    RecordIntegrity,
    Role,
    TurnEntryBody,
    TurnResult,
    VisitStateController,
    VisitStatePublic,
    VoiceSpeaking,
    to_caption,
)
from hash_chain import HashChain
from introduction import CONSENT_NOTICES


class Sender(Protocol):
    async def send_json(self, data: Any) -> None: ...


@dataclass
class TurnRecord:
    result: TurnResult | None
    speaker: str
    source_text: str
    stage: str
    # Settled turns (spoken, blocked, or escalated) are the only ones shared screens see.
    settled: bool = False
    readback_confirmed: bool = False


def now() -> str:
    return datetime.now(UTC).isoformat()


def new_entry_id() -> str:
    """An id for a chain entry that is not a turn (a turn's entry id is its turnId, CDR-006)."""
    return uuid.uuid4().hex[:12]


@dataclass
class Connection:
    sender: Sender
    role: Role
    seq: int = 0
    # Graph nodes run in parallel, so sends are serialised to keep wire order equal to seq order.
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


@dataclass(eq=False)
class Speech:
    """What the interpreter's voice is playing now, and the controller connection that reported it (CDR-004).

    Compared by identity, so a ceiling timer clears only the speech it was started for.
    """

    speech_id: str
    language: str
    conn: Connection

    def is_(self, speech_id: str, language: str) -> bool:
        return (self.speech_id, self.language) == (speech_id, language)


@dataclass
class Visit:
    visit_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    patient_language: str = "pa-IN"
    physician_language: str = "en-CA"
    consent: str | None = None
    paused: bool = False
    turns: dict[str, TurnRecord] = field(default_factory=dict)
    nudges: list[EmpathyNudge] = field(default_factory=list)
    current_turn_id: str | None = None
    pending_readback: str | None = None
    physician_name: str | None = None
    patient_name: str | None = None
    introduction: IntroductionState = "pending"
    # Names heard in a spoken reply, waiting for the physician to confirm them.
    proposed_names: dict[str, str] = field(default_factory=dict)
    # Everything the interpreter said itself, by line id, so it can be spoken again by id (CDR-003).
    interpreter_lines: dict[str, InterpreterLine] = field(default_factory=dict)
    # CDR-004: one voice at a time; None is silent, so a new visit starts silent.
    speech: Speech | None = None
    # ADR-003 and CDR-006: every interpreter offer, request, high-risk mark, and dismissal, in order, each also
    # a chain entry. In the controller's visit.state only, so a reloaded controller still shows them.
    escalations: list[EscalationEntry] = field(default_factory=list)
    # CDR-006: an offer or request is open until the controller dismisses it; every role sees this flag.
    interpreter_open: bool = False
    # TDM-002: the presenter's one-shot mismatch, and the turns it fired on, in order. In the controller's
    # visit.state only (CDR-006), never in a public snapshot.
    injection_armed: bool = False
    injected_turns: list[str] = field(default_factory=list)
    # CDR-005: the latest consent change (None before the first), and the notices already read aloud on their own.
    consent_state: ConsentState | None = None
    consent_spoken: set[str] = field(default_factory=set)
    # Raised by every withdrawal, so a turn that was in the graph when consent was withdrawn is discarded.
    consent_epoch: int = 0
    # IDR-003 and CDR-006: the append-only record, and each entry's entryId by chain index, so a failed
    # verification is named by the id the server recorded, whatever the stored payload now says.
    chain: HashChain = field(default_factory=HashChain)
    entry_ids: list[str] = field(default_factory=list)

    def names(self) -> Names:
        return Names(physician_name=self.physician_name, patient_name=self.patient_name)

    def speaking(self) -> VoiceSpeaking:
        if self.speech is None:
            return SILENT
        return VoiceSpeaking(speaking=True, speech_id=self.speech.speech_id, language=self.speech.language)  # type: ignore[arg-type]

    def consent_notice(self) -> ConsentNotice | None:
        """The reviewed notice for the visit's patient language, or None if that language has none."""
        return CONSENT_NOTICES.get(self.patient_language)

    def append(self, kind: EntryKind, entry_id: str, body: dict, at: str | None = None) -> RecordEntry:
        """Append one typed entry to the record chain (CDR-006); nothing in the chain is ever edited."""
        entry = RecordEntry(entry_id=entry_id, kind=kind, at=at or now(), body=body)
        self.chain.append(entry.wire())
        self.entry_ids.append(entry_id)
        return entry

    def append_turn(self, turn_id: str) -> RecordEntry:
        """A settled turn's entry: its public caption and the names it was relayed with, nothing private."""
        record = self.turns[turn_id]
        assert record.result is not None and record.settled
        caption = to_caption(record.result, record.readback_confirmed)
        body = TurnEntryBody(
            **caption.model_dump(),
            settled_as=caption.status,
            physician_name=self.physician_name,
            patient_name=self.patient_name,
        )
        return self.append("turn", turn_id, body.wire())

    def integrity(self) -> RecordIntegrity:
        """record.integrity: brokenAt is the entryId of the first entry that fails, a turn's segmentId (CDR-006)."""
        verification = self.chain.verify()
        if verification.ok:
            return RecordIntegrity(status="verified", head_hash=verification.head_hash)
        index = verification.broken_at
        assert index is not None
        broken_at = self.entry_ids[index] if index < len(self.entry_ids) else None
        return RecordIntegrity(status="broken", head_hash=verification.head_hash, broken_at=broken_at)

    def snapshot(self, role: Role) -> dict:
        """visit.state filtered by role exactly like live events (CDR-001)."""
        notice = self.consent_notice()
        if role == "controller":
            current = self.turns.get(self.current_turn_id) if self.current_turn_id else None
            return VisitStateController(
                patient_language=self.patient_language,  # type: ignore[arg-type]
                physician_language=self.physician_language,  # type: ignore[arg-type]
                consent=self.consent,
                paused=self.paused,
                turns=[t.result for t in self.turns.values() if t.result is not None],
                current_turn=current.result if current else None,
                pending_readback=self.pending_readback,
                nudges=self.nudges,
                integrity=self.integrity(),
                physician_name=self.physician_name,
                patient_name=self.patient_name,
                introduction=self.introduction,
                speaking=self.speaking(),
                consent_notice=notice,
                consent_state=self.consent_state,
                interpreter_open=self.interpreter_open,
                injection=InjectionStatus(
                    state="armed" if self.injection_armed else "idle", injected_turn_ids=self.injected_turns
                ),
                escalations=self.escalations,
            ).wire()

        current_public = None
        if self.current_turn_id:
            t = self.turns[self.current_turn_id]
            if not t.settled:
                current_public = CurrentTurnPublic(
                    turn_id=self.current_turn_id,
                    speaker=t.speaker,  # type: ignore[arg-type]
                    source_text=t.source_text,
                    stage=t.stage,
                )
        return VisitStatePublic(
            patient_language=self.patient_language,  # type: ignore[arg-type]
            physician_language=self.physician_language,  # type: ignore[arg-type]
            consent=self.consent,
            paused=self.paused,
            turns=[
                to_caption(t.result, t.readback_confirmed)
                for t in self.turns.values()
                if t.settled and t.result is not None
            ],
            current_turn=current_public,
            integrity=self.integrity(),
            physician_name=self.physician_name,
            patient_name=self.patient_name,
            introduction=self.introduction,
            speaking=self.speaking(),
            consent_notice=notice,
            consent_state=self.consent_state,
            interpreter_open=self.interpreter_open,
        ).wire()


class Hub:
    """Fans events out to connections, never sending controller-only events to screens."""

    def __init__(self, visit: Visit) -> None:
        self.visit = visit
        self.connections: list[Connection] = []

    def add(self, sender: Sender, role: Role) -> Connection:
        conn = Connection(sender=sender, role=role)
        self.connections.append(conn)
        return conn

    def remove(self, conn: Connection) -> None:
        if conn in self.connections:
            self.connections.remove(conn)

    def _envelope(self, conn: Connection, event_type: str, payload: dict) -> dict:
        # seq is per connection so a screen sees no gaps for events it is not allowed to receive.
        conn.seq += 1
        return Envelope(
            type=event_type,
            visit_id=self.visit.visit_id,
            seq=conn.seq,
            ts=now(),
            payload=payload,
        ).wire()

    async def send_to(self, conn: Connection, event_type: str, payload: dict) -> None:
        if event_type in CONTROLLER_ONLY_EVENTS and conn.role != "controller":
            return
        async with conn.lock:
            try:
                await conn.sender.send_json(self._envelope(conn, event_type, payload))
            except Exception:
                self.remove(conn)

    async def publish(self, event_type: str, payload: dict) -> None:
        for conn in list(self.connections):
            await self.send_to(conn, event_type, payload)

    async def send_state(self, conn: Connection) -> None:
        await self.send_to(conn, "visit.state", self.visit.snapshot(conn.role))

    async def publish_state(self) -> None:
        for conn in list(self.connections):
            await self.send_state(conn)
