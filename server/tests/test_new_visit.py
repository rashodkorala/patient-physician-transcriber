"""Starting a new visit on the visit channel (CDR-001 `visit.new`, ADR-007): every role gets a fresh visit.state,
the old visit's running work never publishes into the new one, the voice is silenced, and only the controller may
start one, against the full turn graph with the scripted model (EDR-002)."""

import asyncio
import threading
import time

import pytest
from test_visit_channel import (
    drain_until,
    drain_until_stage,
    kb,  # noqa: F401  (fixture)
    make_client,
    submit,
    types,
)
from visit_helpers import (
    CHEST,
    CHEST_CORRECTED,
    SAID_IN_FULL,
    close,
    command,
    connect,
    marker,
    patient_says,
    speak_plan,
    translate,
    visit,
)

import fake_model
from contracts import CONTROLLER_COMMANDS, REVIEW_COMMANDS, REVIEW_OR_CONTROLLER_COMMANDS
from hash_chain import EMPTY_HEAD

WORRIED_PA = "I am scared, ਮੈਨੂੰ ਬਹੁਤ ਡਰ ਲੱਗਦਾ ਹੈ।"
# Events that would mean the old visit's work reached the new one.
OLD_WORK = {
    "turn.started",
    "turn.status",
    "turn.analysis",
    "turn.result",
    "turn.readback_required",
    "record.integrity",
    "empathy.nudge",
    "trust.update",
    "interpreter.escalation",
    "segment.status",
    "segment.analysis",
    "segment.amended",
    "explainback.state",
    "explainback.result",
    "note.status",
    "note.ready",
    "summary.status",
    "summary.check",
    "summary.ready",
    "artefacts.stale",
    "voice.speaking",
    "demo.injection_state",
    "error",
}


def new_visit(client, ctl, *others):
    """Send `visit.new` from `ctl` and wait for every socket's new visit.state; returns the new visit and the
    envelopes, controller first."""
    old_id = visit(client).visit_id
    command(ctl, "visit.new")
    envelopes = [fresh_state(ws, old_id) for ws in (ctl, *others)]
    return visit(client), envelopes


def fresh_state(ws, old_id: str) -> dict:
    """The envelope of the visit.state that `visit.new` sent this connection: the first one for another visit (a
    turn's own visit.state, sent when it skips the introduction, carries the old visitId)."""
    while True:
        envelope = drain_until(ws, "visit.state")[-1]
        if envelope["visitId"] != old_id:
            return envelope


def gated(handler, when=lambda user: True):
    """A model handler whose first matching call waits until the returned gate is set, then answers as `handler`."""
    gate, held = threading.Event(), []

    async def run(user):
        if when(user) and not held:
            held.append(user)
            while not gate.is_set():
                await asyncio.sleep(0.01)
        return handler(user)

    return run, gate, held


def wait_until(condition, timeout=5.0):
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "timed out"
        time.sleep(0.01)


def wait_idle(client):
    """Every background run (turns, the advisor, corrections, checks, the note, and the summary) has finished."""
    wait_until(lambda: not client.app.state.background)


def assert_untouched(new, client, ctl, *others):
    """Nothing reached the new visit: no event on any socket before the marker, and an empty visit and chain."""
    ctl_events, other_events = marker(ctl, *others)
    for events in (ctl_events, *other_events):
        assert not OLD_WORK & set(types(events)), types(events)
    current = visit(client)
    assert current is new
    assert current.turns == {} and current.trust == [] and current.nudges == [] and current.signals == []
    assert not current.chain.entries and current.explain_back is None and current.explain_back_results == []
    assert current.note is None and current.summary is None and current.summary_checks == []
    assert current.segments == {}


# ---------- every role starts again (CDR-001) ----------


def test_new_visit_sends_every_role_a_fresh_state_with_a_new_visit_id_cdr_001(kb):  # noqa: F811
    with make_client(kb, translate=translate) as client:
        sockets, (ctl, tv, phone) = connect(client, "controller", "screen", "review")
        try:
            old_id = visit(client).visit_id
            command(ctl, "visit.set_names", physicianName="Dr Rao", patientName="Mr Singh")
            submit(ctl, "physician", "en-CA", "Hello.")
            drain_until(ctl, "trust.update")
            patient_says(ctl, CHEST)
            drain_until(ctl, "trust.update")
            for ws in (tv, phone):
                drain_until(ws, "turn.result"), drain_until(ws, "turn.result"), drain_until(ws, "record.integrity")
            command(phone, "patient.signal", signal="not_understood")
            drain_until(ctl, "trust.update"), drain_until(tv, "patient.signal")
            assert len(visit(client).chain.entries) > 0

            new, envelopes = new_visit(client, ctl, tv, phone)
            states = dict(zip(("controller", "screen", "review"), envelopes, strict=True))
            new_id = new.visit_id
            assert new_id != old_id
            for role, envelope in states.items():
                state = envelope["payload"]
                assert envelope["visitId"] == new_id, role
                assert state["turns"] == [] and state["signals"] == [] and state["consent"] is None, role
                assert state["currentTurn"] is None and state["consentState"] is None, role
                assert state["physicianName"] is None and state["patientName"] is None, role
                assert state["introduction"] == "pending" and state["interpreterOpen"] is False, role
                assert state["speaking"]["speaking"] is False, role
                assert state["integrity"] == {"status": "verified", "headHash": EMPTY_HEAD, "brokenAt": None}, role
                assert state["patientLanguage"] == "pa-IN" and state["physicianLanguage"] == "en-CA", role
            controller = states["controller"]["payload"]
            assert controller["trust"] == [] and controller["nudges"] == [] and controller["escalations"] == []
            assert controller["pendingReadback"] is None and controller["tamper"] is None
            assert controller["injection"] == {"state": "idle", "injectedTurnIds": []}
            assert not visit(client).chain.entries
            # Later events carry the new visitId too.
            events, others = marker(ctl, tv, phone)
            assert {e["visitId"] for e in [events[-1], *(o[-1] for o in others)]} == {new_id}
        finally:
            close(sockets)
        # A connection opened afterwards sees the new visit, empty.
        with client.websocket_connect("/ws/visit?role=review") as late:
            envelope = late.receive_json()
            assert envelope["visitId"] == visit(client).visit_id and envelope["payload"]["turns"] == []


def test_health_reports_the_new_visit_id_cdr_001(kb):  # noqa: F811
    with make_client(kb) as client:
        before = client.get("/api/health").json()["visitId"]
        sockets, (ctl,) = connect(client, "controller")
        try:
            _, (state,) = new_visit(client, ctl)
        finally:
            close(sockets)
        after = client.get("/api/health").json()["visitId"]
        assert after != before and after == state["visitId"] == visit(client).visit_id


def test_visit_new_is_a_controller_command_cdr_001():
    assert "visit.new" in CONTROLLER_COMMANDS
    assert "visit.new" not in REVIEW_OR_CONTROLLER_COMMANDS | REVIEW_COMMANDS


def test_new_visit_from_a_screen_is_dropped_and_from_review_is_refused_cdr_001(kb):  # noqa: F811
    with make_client(kb) as client:
        sockets, (ctl, tv, phone) = connect(client, "controller", "screen", "review")
        try:
            before = visit(client)
            command(tv, "visit.new")
            command(phone, "visit.new")
            refused = drain_until(phone, "command.refused")[-1]["payload"]
            assert refused == {"command": "visit.new", "reason": "not_allowed"}
            ctl_events, (tv_events, phone_events) = marker(ctl, tv, phone)
            for events in (ctl_events, tv_events, phone_events):
                assert "visit.state" not in types(events) and "error" not in types(events)
            assert "command.refused" not in types(tv_events)
            assert visit(client) is before and before.consent is not None
        finally:
            close(sockets)


def test_new_visit_during_a_readback_or_an_open_explain_back_clears_them_cdr_001(kb):  # noqa: F811
    with make_client(kb, translate=translate) as client:
        sockets, (ctl, tv) = connect(client, "controller", "screen")
        try:
            submit(ctl, "physician", "en-CA", "Take metformin 500 milligrams twice a day.")
            turn_id = drain_until_stage(ctl, "awaiting_readback")[-1]["payload"]["turnId"]
            _, (controller, screen) = new_visit(client, ctl, tv)
            assert controller["payload"]["pendingReadback"] is None and controller["payload"]["currentTurn"] is None
            assert screen["payload"]["currentTurn"] is None
            # The old dose cannot be confirmed into the new visit.
            command(ctl, "turn.readback_confirm", turnId=turn_id)
            assert drain_until(ctl, "error")[-1]["payload"]["command"] == "turn.readback_confirm"
            assert client.get(f"/api/speech/{turn_id}").status_code == 404
        finally:
            close(sockets)

    with make_client(kb, translate=translate) as client:
        sockets, (ctl, tv) = connect(client, "controller", "screen")
        try:
            speak_plan(ctl)
            command(ctl, "explainback.start")
            explain_back = drain_until(ctl, "explainback.state")[-1]["payload"]
            assert explain_back["state"] == "listening"
            _, envelopes = new_visit(client, ctl, tv)
            assert all(e["payload"]["explainBack"] is None for e in envelopes)
            command(ctl, "explainback.check", explainBackId=explain_back["explainBackId"])
            assert drain_until(ctl, "error")[-1]["payload"]["command"] == "explainback.check"
        finally:
            close(sockets)


def test_new_visit_silences_the_voice_and_cancels_its_ceiling_cdr_001(kb):  # noqa: F811
    with make_client(kb, voice_ceiling_s=0.3) as client:
        sockets, (ctl, tv) = connect(client, "controller", "screen")
        try:
            submit(ctl, "physician", "en-CA", "Hello.")
            turn_id = drain_until(ctl, "trust.update")[-1]["payload"]["turnId"]
            drain_until(tv, "record.integrity")
            command(ctl, "voice.started", speechId=turn_id, language="pa-IN")
            assert drain_until(tv, "voice.speaking")[-1]["payload"]["speaking"] is True
            assert len(client.app.state.ceilings) == 1
            _, envelopes = new_visit(client, ctl, tv)
            assert all(e["payload"]["speaking"]["speaking"] is False for e in envelopes)
            assert visit(client).speech is None
            wait_until(lambda: not client.app.state.ceilings)
            # Past the ceiling, nothing is published for the old speech.
            time.sleep(0.4)
            ctl_events, (tv_events,) = marker(ctl, tv)
            assert "voice.speaking" not in types(ctl_events) + types(tv_events)
            # And the old turn is not speakable in the new visit.
            command(ctl, "voice.started", speechId=turn_id, language="pa-IN")
            assert drain_until(ctl, "error")[-1]["payload"]["command"] == "voice.started"
        finally:
            close(sockets)


# ---------- the old visit's running work never reaches the new one (CDR-001, CDR-005 consent rule 3) ----------


def test_a_turn_in_the_graph_never_publishes_into_the_new_visit_cdr_001(kb):  # noqa: F811
    handler, gate, held = gated(translate)
    with make_client(kb, translate=handler) as client:
        sockets, (ctl, tv) = connect(client, "controller", "screen")
        try:
            submit(ctl, "physician", "en-CA", "Hello.")
            turn_id = drain_until(ctl, "turn.started")[-1]["payload"]["turnId"]
            wait_until(lambda: held)
            new, _ = new_visit(client, ctl, tv)
            gate.set()
            wait_idle(client)
            assert_untouched(new, client, ctl, tv)
            assert client.get(f"/api/speech/{turn_id}").status_code == 404
        finally:
            close(sockets)


def test_the_trust_advisor_never_publishes_into_the_new_visit_cdr_001(kb):  # noqa: F811
    handler, gate, held = gated(fake_model.trust)
    with make_client(kb, handlers={"trust": handler}) as client:
        sockets, (ctl, tv) = connect(client, "controller", "screen")
        try:
            submit(ctl, "patient", "pa-IN", WORRIED_PA)
            drain_until(ctl, "turn.result"), drain_until(tv, "record.integrity")
            wait_until(lambda: held)
            new, _ = new_visit(client, ctl, tv)
            gate.set()
            wait_idle(client)
            assert_untouched(new, client, ctl, tv)
        finally:
            close(sockets)


def test_a_correction_being_checked_never_publishes_into_the_new_visit_cdr_001(kb):  # noqa: F811
    handler, gate, held = gated(translate, when=lambda user: CHEST_CORRECTED[0] in user)
    with make_client(kb, translate=handler) as client:
        sockets, (ctl, tv, phone) = connect(client, "controller", "screen", "review")
        try:
            segment_id = patient_says(ctl, CHEST)["turnId"]
            drain_until(ctl, "trust.update")
            drain_until(phone, "record.integrity"), drain_until(tv, "record.integrity")
            command(
                phone,
                "segment.amend",
                segmentId=segment_id,
                text=CHEST_CORRECTED[0],
                language="pa-IN",
                recognitionConfidence=0.9,
            )
            wait_until(lambda: held)
            new, _ = new_visit(client, ctl, tv, phone)
            gate.set()
            wait_idle(client)
            assert_untouched(new, client, ctl, tv, phone)
        finally:
            close(sockets)


def test_an_explain_back_being_checked_never_publishes_into_the_new_visit_cdr_001(kb):  # noqa: F811
    handler, gate, held = gated(fake_model.explain_back)
    with make_client(kb, translate=translate, handlers={"explain_back": handler}) as client:
        sockets, (ctl, tv) = connect(client, "controller", "screen")
        try:
            speak_plan(ctl)
            command(ctl, "explainback.start")
            explain_back_id = drain_until(ctl, "explainback.state")[-1]["payload"]["explainBackId"]
            patient_says(ctl, SAID_IN_FULL)
            drain_until(ctl, "explainback.state")
            command(ctl, "explainback.check", explainBackId=explain_back_id)
            wait_until(lambda: held)
            new, _ = new_visit(client, ctl, tv)
            gate.set()
            wait_idle(client)
            assert_untouched(new, client, ctl, tv)
        finally:
            close(sockets)


@pytest.mark.parametrize(
    ("purpose", "command_type"),
    [("clinical_note", "note.generate"), ("patient_summary", "summary.generate")],
)
def test_a_note_or_summary_being_written_never_publishes_into_the_new_visit_cdr_001(kb, purpose, command_type):  # noqa: F811
    handler, gate, held = gated(getattr(fake_model, purpose))
    with make_client(kb, translate=translate, handlers={purpose: handler}) as client:
        sockets, (ctl, tv) = connect(client, "controller", "screen")
        try:
            speak_plan(ctl)
            patient_says(ctl, CHEST)
            drain_until(ctl, "trust.update")
            command(ctl, command_type)
            wait_until(lambda: held)
            new, _ = new_visit(client, ctl, tv)
            gate.set()
            wait_idle(client)
            assert_untouched(new, client, ctl, tv)
        finally:
            close(sockets)
