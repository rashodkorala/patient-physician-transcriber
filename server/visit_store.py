"""One in-memory visit and the connections watching it.

@implements ADR-007: In-memory visit state with WebSocket updates; no database for the demo
@implements CDR-001: Visit WebSocket event contract
@contract ws:/ws/visit
@see openspec/tdr/adr/adr-007-in-memory-state-websocket.md
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from contracts import (
    CONTROLLER_ONLY_EVENTS,
    CurrentTurnPublic,
    EmpathyNudge,
    Envelope,
    RecordIntegrity,
    Role,
    TurnResult,
    VisitStateController,
    VisitStatePublic,
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


@dataclass
class Connection:
    sender: Sender
    role: Role
    seq: int = 0


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
            ts=datetime.now(timezone.utc).isoformat(),
            payload=payload,
        ).wire()

    async def send_to(self, conn: Connection, event_type: str, payload: dict) -> None:
        if event_type in CONTROLLER_ONLY_EVENTS and conn.role != "controller":
            return
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
