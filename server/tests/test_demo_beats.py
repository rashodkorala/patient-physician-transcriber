"""Visit channel tests for the remaining demo beats: the off-the-record pause, the human interpreter request,
the physician's high-risk mark (task 3.3, ADR-003, CDR-001), and the presenter mismatch control (task 5.1,
TDM-002, CDR-001, CDR-002)."""

import pytest
from test_visit_channel import (
    DOSE,
    command,
    contains_private,
    drain_until,
    drain_until_stage,
    kb,  # noqa: F401  (fixture)
    make_client,
    set_names,
    submit,
    types,
)

INJECTION_WORDS = ("injection", "inject", "armed", "fired")


@pytest.fixture
def client(kb):  # noqa: F811
    with make_client(kb) as c:
        yield c


def connect(client, *roles):
    sockets = [client.websocket_connect(f"/ws/visit?role={role}") for role in roles]
    opened = [s.__enter__() for s in sockets]
    for ws in opened:
        assert ws.receive_json()["type"] == "visit.state"
    return sockets, opened


def close(sockets):
    for s in reversed(sockets):
        s.__exit__(None, None, None)


def marker(ctl, *others):
    """A public event every role receives; anything published before it has arrived by then."""
    set_names(ctl, patientName="Marker")
    seen = [drain_until(ws, "visit.names") for ws in others]
    return drain_until(ctl, "visit.names"), seen


def mentions_injection(events) -> bool:
    return any(word in str(e).lower() for e in events for word in INJECTION_WORDS)


# ---------- off-the-record pause (task 3.3) ----------


def test_pause_reaches_every_role_and_the_snapshot_cdr_001(client):
    sockets, (ctl, tv) = connect(client, "controller", "screen")
    try:
        command(ctl, "visit.pause")
        assert drain_until(tv, "visit.paused")[-1]["payload"] == {}
        assert drain_until(ctl, "visit.paused")
        with client.websocket_connect("/ws/visit?role=screen") as late:
            assert late.receive_json()["payload"]["paused"] is True
        command(ctl, "visit.resume")
        assert drain_until(tv, "visit.resumed")
        with client.websocket_connect("/ws/visit?role=screen") as late:
            assert late.receive_json()["payload"]["paused"] is False
    finally:
        close(sockets)


def test_any_screen_may_pause_and_resume_cdr_001(client):
    sockets, (ctl, tv) = connect(client, "controller", "screen")
    try:
        command(tv, "visit.pause")
        assert drain_until(ctl, "visit.paused")
        command(tv, "visit.resume")
        assert drain_until(ctl, "visit.resumed")
    finally:
        close(sockets)


def test_nothing_is_captured_while_paused(client):
    sockets, (ctl, tv) = connect(client, "controller", "screen")
    try:
        command(ctl, "visit.pause")
        drain_until(ctl, "visit.paused")
        submit(ctl, "patient", "pa-IN", "ਮੈਂ ਗੋਲੀਆਂ ਨਹੀਂ ਲਈਆਂ।")
        error = drain_until(ctl, "error")[-1]["payload"]
        assert error["command"] == "turn.submit" and "Paused" in error["message"]
        command(ctl, "visit.start_introduction")
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "visit.start_introduction"
        command(ctl, "visit.resume")
        tv_events = drain_until(tv, "visit.resumed")
        assert "turn.started" not in types(tv_events)
        assert client.app.state.hub.visit.turns == {}
        submit(ctl, "patient", "pa-IN", "ਸਤ ਸ੍ਰੀ ਅਕਾਲ")
        assert drain_until(tv, "turn.result")[-1]["payload"]["sourceText"] == "ਸਤ ਸ੍ਰੀ ਅਕਾਲ"
    finally:
        close(sockets)


def test_pause_twice_or_resume_unpaused_is_refused(client):
    sockets, (ctl,) = connect(client, "controller")
    try:
        command(ctl, "visit.resume")
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "visit.resume"
        command(ctl, "visit.pause")
        drain_until(ctl, "visit.paused")
        command(ctl, "visit.pause")
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "visit.pause"
    finally:
        close(sockets)


# ---------- human interpreter and high-risk marks (task 3.3, ADR-003) ----------


def test_interpreter_request_from_any_screen_reaches_every_role_and_is_recorded_adr_003(client):
    sockets, (ctl, tv) = connect(client, "controller", "screen")
    try:
        command(tv, "interpreter.request")
        assert drain_until(ctl, "interpreter.escalation")[-1]["payload"] == {"reason": "requested", "turnId": None}
        assert drain_until(tv, "interpreter.escalation")[-1]["payload"]["reason"] == "requested"
        command(ctl, "interpreter.request")
        drain_until(tv, "interpreter.escalation")
        records = client.app.state.hub.visit.escalations
        assert [r.reason for r in records] == ["requested", "requested"] and all(r.at for r in records)
    finally:
        close(sockets)


def test_mark_high_risk_offers_an_interpreter_with_reason_high_risk_cdr_001(client):
    sockets, (ctl, tv) = connect(client, "controller", "screen")
    try:
        command(ctl, "visit.mark_high_risk")
        assert drain_until(tv, "interpreter.escalation")[-1]["payload"] == {"reason": "high_risk", "turnId": None}
        assert drain_until(ctl, "interpreter.escalation")[-1]["payload"]["reason"] == "high_risk"
        record = client.app.state.hub.visit.escalations[-1]
        assert record.reason == "high_risk" and record.turn_id is None
    finally:
        close(sockets)


def test_mark_high_risk_on_a_turn_keeps_its_id_and_note_cdr_001(client):
    sockets, (ctl, tv) = connect(client, "controller", "screen")
    try:
        submit(ctl, "physician", "en-CA", "I'd like to refer you for an angiogram.")
        turn_id = drain_until(ctl, "turn.result")[-1]["payload"]["turnId"]
        command(ctl, "visit.mark_high_risk", turnId=turn_id, note="  Consent   to a procedure ")
        escalation = drain_until(tv, "interpreter.escalation")[-1]["payload"]
        # The note stays in the record; the public event carries only the reason and the turn.
        assert escalation == {"reason": "high_risk", "turnId": turn_id}
        record = client.app.state.hub.visit.escalations[-1]
        assert (record.turn_id, record.note) == (turn_id, "Consent to a procedure")
    finally:
        close(sockets)


def test_mark_high_risk_refuses_an_unknown_turn_and_a_bad_payload(client):
    sockets, (ctl,) = connect(client, "controller")
    try:
        command(ctl, "visit.mark_high_risk", turnId="nope")
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "visit.mark_high_risk"
        command(ctl, "visit.mark_high_risk", priority="urgent")
        assert "Invalid payload" in drain_until(ctl, "error")[-1]["payload"]["message"]
        assert client.app.state.hub.visit.escalations == []
    finally:
        close(sockets)


def test_screen_cannot_mark_high_risk_cdr_001(client):
    sockets, (tv, ctl) = connect(client, "screen", "controller")
    try:
        command(tv, "visit.mark_high_risk")
        (ctl_events, (tv_events,)) = marker(ctl, tv)
        assert "interpreter.escalation" not in types(ctl_events) + types(tv_events)
        assert client.app.state.hub.visit.escalations == []
    finally:
        close(sockets)


def test_automatic_escalation_is_recorded_too_adr_003(kb):  # noqa: F811
    from graph.turn_graph import ToneCheck

    def failing(user):
        return ToneCheck(meaning_preserved=True, certainty_preserved=False, warmth_preserved=True, issue="x")

    with make_client(kb, tone_check=failing) as client:
        sockets, (ctl,) = connect(client, "controller")
        try:
            submit(ctl, "physician", "en-CA", "This is very unlikely to be serious.")
            drain_until(ctl, "interpreter.escalation")
            record = client.app.state.hub.visit.escalations[-1]
            assert record.reason == "tone_failure" and record.turn_id
        finally:
            close(sockets)


# ---------- presenter mismatch control (task 5.1, TDM-002) ----------


def injection(event):
    assert event["type"] == "demo.injection_state", event["type"]
    return event["payload"]["state"]


def test_armed_injection_waits_then_blocks_the_next_dose_on_both_attempts_tdm_002(client):
    sockets, (ctl, tv) = connect(client, "controller", "screen")
    try:
        command(ctl, "demo.inject_mismatch")
        assert injection(ctl.receive_json()) == "armed"

        # A physician turn without a critical value, and a patient turn with one, leave it armed.
        submit(ctl, "physician", "en-CA", "You did not have a heart attack.")
        assert "demo.injection_state" not in types(drain_until(ctl, "turn.result"))
        submit(ctl, "patient", "pa-IN", "ਮੈਂ 2 ਗੋਲੀਆਂ ਲਈਆਂ।")
        assert "demo.injection_state" not in types(drain_until(ctl, "turn.result"))
        assert client.app.state.hub.visit.injection_armed is True

        submit(ctl, "physician", "en-CA", DOSE)
        events = drain_until(ctl, "turn.result")
        assert [injection(e) for e in events if e["type"] == "demo.injection_state"] == ["fired"]
        # Fired before the analysis, so the controller can mark the turn as it settles.
        assert types(events).index("demo.injection_state") < types(events).index("turn.analysis")
        analysis = next(e for e in events if e["type"] == "turn.analysis")["payload"]
        assert analysis["status"] == "blocked" and analysis["attempts"] == 2
        assert "4 ਮਿਲੀਗ੍ਰਾਮ" in analysis["translation"] and "0.4" not in analysis["translation"]
        blocked_id = analysis["turnId"]
        assert client.app.state.hub.visit.injected_turns == [blocked_id]

        # The repeat is unaffected and goes to read-back.
        submit(ctl, "physician", "en-CA", DOSE)
        repeat = drain_until_stage(ctl, "awaiting_readback")
        assert "demo.injection_state" not in types(repeat)
        analysis = next(e for e in repeat if e["type"] == "turn.analysis")["payload"]
        assert analysis["status"] == "readback_required" and "0.4" in analysis["translation"]

        tv_events = drain_until_stage(tv, "awaiting_readback")
        blocked = next(e for e in tv_events if e["type"] == "turn.result" and e["payload"]["turnId"] == blocked_id)
        assert blocked["payload"]["status"] == "blocked" and blocked["payload"]["translation"] is None
        assert not mentions_injection(tv_events) and not contains_private(tv_events)
        assert "4 ਮਿਲੀਗ੍ਰਾਮ" not in str(tv_events)
    finally:
        close(sockets)


def test_cancelled_injection_leaves_the_next_dose_alone_tdm_002(client):
    sockets, (ctl, tv) = connect(client, "controller", "screen")
    try:
        command(ctl, "demo.inject_mismatch")
        assert injection(ctl.receive_json()) == "armed"
        command(ctl, "demo.cancel_injection")
        assert injection(ctl.receive_json()) == "cancelled"
        submit(ctl, "physician", "en-CA", DOSE)
        events = drain_until_stage(ctl, "awaiting_readback")
        assert "demo.injection_state" not in types(events)
        assert next(e for e in events if e["type"] == "turn.analysis")["payload"]["status"] == "readback_required"
        assert not mentions_injection(drain_until_stage(tv, "awaiting_readback"))
    finally:
        close(sockets)


def test_cancel_without_an_armed_injection_is_refused_tdm_002(client):
    sockets, (ctl,) = connect(client, "controller")
    try:
        command(ctl, "demo.cancel_injection")
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "demo.cancel_injection"
    finally:
        close(sockets)


@pytest.mark.parametrize("role", ["screen", "review"])
def test_injection_commands_are_refused_from_other_roles_tdm_002(client, role):
    sockets, (other, ctl) = connect(client, role, "controller")
    try:
        command(other, "demo.inject_mismatch")
        command(other, "demo.cancel_injection")
        ctl_events, (other_events,) = marker(ctl, other)
        assert "demo.injection_state" not in types(ctl_events) + types(other_events)
        assert client.app.state.hub.visit.injection_armed is False
    finally:
        close(sockets)


@pytest.mark.parametrize("role", ["screen", "review"])
def test_injection_state_never_reaches_screens_live_or_by_snapshot_tdm_002(client, role):
    sockets, (ctl, other) = connect(client, "controller", role)
    try:
        command(ctl, "demo.inject_mismatch")
        assert injection(ctl.receive_json()) == "armed"
        _, (other_events,) = marker(ctl, other)
        assert not mentions_injection(other_events)
        with client.websocket_connect(f"/ws/visit?role={role}") as late:
            state = late.receive_json()
            assert state["type"] == "visit.state" and not mentions_injection([state])
            set_names(ctl, patientName="Again")
            assert late.receive_json()["type"] == "visit.names"  # nothing about the injection came first
    finally:
        close(sockets)


def test_reconnecting_controller_sees_the_armed_injection_tdm_002(client):
    sockets, (ctl,) = connect(client, "controller")
    try:
        command(ctl, "demo.inject_mismatch")
        assert injection(ctl.receive_json()) == "armed"
        with client.websocket_connect("/ws/visit?role=controller") as again:
            assert again.receive_json()["type"] == "visit.state"
            assert injection(again.receive_json()) == "armed"
    finally:
        close(sockets)
