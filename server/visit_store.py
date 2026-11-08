"""One in-memory visit and the connections watching it.

@implements ADR-007: In-memory visit state with WebSocket updates; no database for the demo
@implements CDR-001: Visit WebSocket event contract
@implements CDR-003: Participant names and interpreter lines on the visit channel
@implements CDR-004: Interpreter voice playback on the visit channel
@implements ADR-003: Human interpreter escalation on low confidence and high-risk moments
@implements TDM-002: Presenter mismatch control for the blocked-dose beat
@contract ws:/ws/visit
@see openspec/tdr/adr/adr-007-in-memory-state-websocket.md
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from contracts import (
    CONTROLLER_ONLY_EVENTS,
    SILENT,
    CurrentTurnPublic,
    EmpathyNudge,
    Envelope,
    EscalationReason,
    InterpreterLine,
    IntroductionState,
    Names,
    RecordIntegrity,
    Role,
    TurnResult,
    VisitStateController,
    VisitStatePublic,
    VoiceSpeaking,
    to_caption,
)


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


@dataclass(frozen=True)
class EscalationRecord:
    """An interpreter offer or request, or a physician's high-risk mark, as recorded in the visit (ADR-003)."""

    reason: EscalationReason
    at: str
    turn_id: str | None = None
    note: str | None = None


def now() -> str:
    return datetime.now(UTC).isoformat()


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
    # ADR-003: every interpreter offer and request, and every high-risk mark, in order. Kept with the
    # visit as its transcript record; no visit.state field carries it (CDR-001 defines none).
    escalations: list[EscalationRecord] = field(default_factory=list)
    # TDM-002: the presenter's one-shot mismatch, and the turns it fired on. Never in a public snapshot,
    # and not in the controller's either, which CDR-001 gives no field for.
    injection_armed: bool = False
    injected_turns: set[str] = field(default_factory=set)

    def names(self) -> Names:
        return Names(physician_name=self.physician_name, patient_name=self.patient_name)

    def speaking(self) -> VoiceSpeaking:
        if self.speech is None:
            return SILENT
        return VoiceSpeaking(speaking=True, speech_id=self.speech.speech_id, language=self.speech.language)  # type: ignore[arg-type]

    def integrity(self) -> RecordIntegrity:
        # Hash chain arrives with IDR-003 (task 3.8); an empty chain is verified.
        return RecordIntegrity(status="verified", head_hash="")

    def snapshot(self, role: Role) -> dict:
        """visit.state filtered by role exactly like live events (CDR-001)."""
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
