"""The visit's record chain (CDR-006, IDR-003): typed entries for settled turns, consent changes, and interpreter
events; record.integrity after every append, with brokenAt naming the first altered entry; interpreter.dismiss;
and the controller-only injection and escalations in visit.state.

Tampering here uses HashChain.tamper directly. The presenter's tamper command (TDM-005) is not built."""

import pytest
from test_consent import close, command, connect, marker
from test_visit_channel import (
    DOSE,
    PRIVATE_KEYS,
    contains_private,
    drain_until,
    drain_until_stage,
    kb,  # noqa: F401  (fixture)
    make_client,
    set_names,
    submit,
    types,
    withdraw_consent,
)

import fake_model
from graph.turn_graph import Draft, ToneCheck


@pytest.fixture
def client(kb):  # noqa: F811
    with make_client(kb) as c:
        yield c


def entries(client):
    return [e.payload for e in client.app.state.hub.visit.chain.entries]


def kinds(client):
    return [e["kind"] for e in entries(client)]


def visit(client):
    return client.app.state.hub.visit


def wrong_dose(user):
    d = fake_model.translate(user)
    return Draft(**{**d.model_dump(), "translation": d.translation.replace("0.4", "4")})


def failing_tone(user):
    return ToneCheck(meaning_preserved=True, certainty_preserved=False, warmth_preserved=True, issue="x")


# ---------- what is chained ----------


def test_a_final_turn_is_one_turn_entry_named_by_its_turn_id_cdr_006(client):
    sockets, (ctl, tv) = connect(client, "controller", "screen")
    try:
        set_names(ctl, physicianName="Dr. Thomas")
        submit(ctl, "physician", "en-CA", "Hello.")
        caption = drain_until(tv, "turn.result")[-1]["payload"]
        integrity = tv.receive_json()
        assert integrity["type"] == "record.integrity"
        assert integrity["payload"] == {
            "status": "verified",
            "headHash": visit(client).chain.head_hash,
            "brokenAt": None,
        }
        turn = entries(client)[-1]
        assert turn["kind"] == "turn" and turn["entryId"] == caption["turnId"]
        assert turn["body"] == {**caption, "settledAs": "final", "physicianName": "Dr. Thomas", "patientName": None}
    finally:
        close(sockets)


def test_a_confirmed_readback_is_chained_and_a_rejected_one_is_not_cdr_006(client):
    sockets, (ctl,) = connect(client, "controller")
    try:
        before = len(entries(client))
        submit(ctl, "physician", "en-CA", DOSE)
        rejected = drain_until_stage(ctl, "awaiting_readback")[-1]["payload"]["turnId"]
        ctl.send_json({"type": "turn.readback_reject", "payload": {"turnId": rejected}})
        drain_until_stage(ctl, "discarded")
        assert len(entries(client)) == before
        submit(ctl, "physician", "en-CA", DOSE)
        confirmed = drain_until_stage(ctl, "awaiting_readback")[-1]["payload"]["turnId"]
        ctl.send_json({"type": "turn.readback_confirm", "payload": {"turnId": confirmed}})
        drain_until(ctl, "record.integrity")
        entry = entries(client)[-1]
        assert entry["entryId"] == confirmed and entry["body"]["readbackConfirmed"] is True
        assert entry["body"]["settledAs"] == "final" and "0.4" in entry["body"]["translation"]
        assert len(entries(client)) == before + 1
    finally:
        close(sockets)


def test_a_blocked_turn_is_chained_without_its_translation_cdr_006(kb):  # noqa: F811
    with make_client(kb, translate=wrong_dose) as client:
        sockets, (ctl,) = connect(client, "controller")
        try:
            submit(ctl, "physician", "en-CA", DOSE)
            turn_id = drain_until(ctl, "record.integrity")[-2]["payload"]["turnId"]
            entry = entries(client)[-1]
            assert entry["entryId"] == turn_id and entry["body"]["settledAs"] == "blocked"
            assert entry["body"]["translation"] is None and entry["body"]["criticalValues"] == []
            assert "ਮਿਲੀਗ੍ਰਾਮ" not in str(entries(client))
        finally:
            close(sockets)


def test_an_escalated_turn_and_its_offer_are_two_entries_cdr_006(kb):  # noqa: F811
    with make_client(kb, tone_check=failing_tone) as client:
        sockets, (ctl, tv) = connect(client, "controller", "screen")
        try:
            submit(ctl, "physician", "en-CA", "This is very unlikely to be serious.")
            events = drain_until(tv, "interpreter.escalation")
            turn_id = next(e for e in events if e["type"] == "turn.result")["payload"]["turnId"]
            assert drain_until(tv, "record.integrity")[-1]["payload"]["status"] == "verified"
            turn, offer = entries(client)[-2:]
            assert turn["entryId"] == turn_id and turn["body"]["settledAs"] == "escalated"
            assert turn["body"]["translation"] is None
            assert offer["kind"] == "interpreter"
            assert offer["body"]["action"] == "offer" and offer["body"]["reason"] == "tone_failure"
            assert offer["body"]["turnId"] == turn_id and "entryId" not in offer["body"]
        finally:
            close(sockets)


def test_marks_requests_and_dismissals_are_chained_and_nothing_else_cdr_006(client):
    sockets, (ctl, tv) = connect(client, "controller", "screen")
    try:
        before = kinds(client)
        set_names(ctl, patientName="Harpreet")
        command(ctl, "visit.pause")
        command(ctl, "visit.resume")
        command(ctl, "demo.inject_mismatch")
        command(ctl, "demo.cancel_injection")
        marker(ctl, tv)
        assert kinds(client) == before  # names, pauses, and injection state are never chained

        command(ctl, "visit.mark_high_risk", note="procedure consent")
        command(tv, "interpreter.request")
        command(ctl, "interpreter.dismiss", reason="simulated_call_ended")
        drain_until(tv, "interpreter.dismissed")
        added = entries(client)[len(before) :]
        assert [(e["kind"], e["body"]["action"], e["body"]["reason"]) for e in added] == [
            ("interpreter", "mark", "high_risk"),
            ("interpreter", "request", "requested"),
            ("interpreter", "dismiss", "simulated_call_ended"),
        ]
        assert added[0]["body"]["note"] == "procedure consent"
        assert [e.entry_id for e in visit(client).escalations][-3:] == [e["entryId"] for e in added]
    finally:
        close(sockets)


def test_no_chain_payload_holds_private_fields_cdr_006(kb):  # noqa: F811
    with make_client(kb) as client:
        sockets, (ctl,) = connect(client, "controller")
        try:
            submit(ctl, "patient", "pa-IN", "ਮੈਨੂੰ ਡਰ ਲੱਗਦਾ ਹੈ।")
            drain_until(ctl, "record.integrity")
            submit(ctl, "physician", "en-CA", DOSE)
            turn_id = drain_until_stage(ctl, "awaiting_readback")[-1]["payload"]["turnId"]
            ctl.send_json({"type": "turn.readback_confirm", "payload": {"turnId": turn_id}})
            drain_until(ctl, "record.integrity")
            withdraw_consent(ctl, reason="Patient asked to stop")
            drain_until(ctl, "record.integrity")
            assert not contains_private(entries(client))
            assert not any(key in str(entries(client)) for key in PRIVATE_KEYS | {"injection", "nudge"})
        finally:
            close(sockets)


# ---------- record.integrity and brokenAt ----------


def tamper_text(client, entry_id):
    """Alter one stored entry's text in place, without rehashing, as the demo control would (tests only)."""
    chain = visit(client).chain
    index = visit(client).entry_ids.index(entry_id)
    payload = chain.entries[index].payload
    body = (
        {**payload["body"], "sourceText": "Take 40 milligrams."}
        if payload["kind"] == "turn"
        else {
            **payload["body"],
            "by": "patient",
        }
    )
    chain.tamper(index, payload={**payload, "body": body})


def test_altering_a_turn_names_its_segment_id_in_broken_at_cdr_006(client):
    sockets, (ctl, tv) = connect(client, "controller", "screen")
    try:
        submit(ctl, "physician", "en-CA", "Hello.")
        first = drain_until(tv, "turn.result")[-1]["payload"]["turnId"]
        submit(ctl, "physician", "en-CA", "How are you?")
        drain_until(tv, "turn.result")
        drain_until(tv, "record.integrity")
        assert visit(client).integrity().status == "verified"

        tamper_text(client, first)
        integrity = visit(client).integrity()
        assert integrity.status == "broken" and integrity.broken_at == first

        # The next append tells every role, live, and a late screen sees it in its snapshot.
        submit(ctl, "patient", "pa-IN", "ਠੀਕ ਹਾਂ ਜੀ।")
        live = drain_until(tv, "record.integrity")[-1]["payload"]
        assert live["status"] == "broken" and live["brokenAt"] == first
        assert live["headHash"] == visit(client).chain.head_hash
        with client.websocket_connect("/ws/visit?role=review") as late:
            assert late.receive_json()["payload"]["integrity"]["brokenAt"] == first
    finally:
        close(sockets)


def test_altering_a_consent_entry_names_its_entry_id_cdr_006(client):
    consent_id = visit(client).consent_state.entry_id
    assert visit(client).entry_ids[0] == consent_id
    tamper_text(client, consent_id)
    integrity = visit(client).integrity()
    assert integrity.status == "broken" and integrity.broken_at == consent_id


def test_the_first_broken_entry_is_named_when_two_are_altered_cdr_006(client):
    sockets, (ctl,) = connect(client, "controller")
    try:
        submit(ctl, "physician", "en-CA", "Hello.")
        first = drain_until(ctl, "record.integrity")[-2]["payload"]["turnId"]
        submit(ctl, "physician", "en-CA", "How are you?")
        second = drain_until(ctl, "record.integrity")[-2]["payload"]["turnId"]
        tamper_text(client, second)
        tamper_text(client, first)
        assert visit(client).integrity().broken_at == first
    finally:
        close(sockets)


def test_an_empty_record_is_verified_with_an_empty_head(kb):  # noqa: F811
    with make_client(kb, consent=False) as client, client.websocket_connect("/ws/visit?role=screen") as tv:
        assert tv.receive_json()["payload"]["integrity"] == {"status": "verified", "headHash": "", "brokenAt": None}


# ---------- interpreter.dismiss ----------


@pytest.mark.parametrize("role", ["screen", "review"])
def test_interpreter_dismiss_is_dropped_from_screen_and_review_cdr_006(client, role):
    sockets, (ctl, other) = connect(client, "controller", role)
    try:
        command(ctl, "visit.mark_high_risk")
        drain_until(other, "record.integrity")
        command(other, "interpreter.dismiss", reason="declined")
        _, (events,) = marker(ctl, other)
        assert not {"interpreter.dismissed", "command.refused"} & set(types(events))
        assert visit(client).interpreter_open is True
    finally:
        close(sockets)


def test_interpreter_dismiss_is_refused_with_no_open_offer_cdr_006(client):
    sockets, (ctl,) = connect(client, "controller")
    try:
        before = len(entries(client))
        command(ctl, "interpreter.dismiss", reason="declined")
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "interpreter.dismiss"
        command(ctl, "interpreter.dismiss", reason="not-a-reason")
        assert "Invalid payload" in drain_until(ctl, "error")[-1]["payload"]["message"]
        assert len(entries(client)) == before
    finally:
        close(sockets)


def test_interpreter_dismiss_clears_every_role_and_works_while_paused_cdr_006(client):
    sockets, (ctl, tv, phone) = connect(client, "controller", "screen", "review")
    try:
        command(ctl, "visit.mark_high_risk")
        drain_until(tv, "interpreter.escalation")
        with client.websocket_connect("/ws/visit?role=screen") as late:
            assert late.receive_json()["payload"]["interpreterOpen"] is True
        command(ctl, "visit.pause")
        command(ctl, "interpreter.dismiss", reason="declined")
        for ws in (ctl, tv, phone):
            dismissed = drain_until(ws, "interpreter.dismissed")[-1]["payload"]
            assert dismissed["reason"] == "declined" and dismissed["entryId"] == visit(client).entry_ids[-1]
            assert ws.receive_json()["type"] == "record.integrity"
        assert entries(client)[-1]["body"]["action"] == "dismiss"
        with client.websocket_connect("/ws/visit?role=screen") as late:
            assert late.receive_json()["payload"]["interpreterOpen"] is False
    finally:
        close(sockets)


# ---------- controller-only visit.state ----------


def test_a_reloaded_controller_keeps_injection_and_escalations_cdr_006(client):
    sockets, (ctl, tv) = connect(client, "controller", "screen")
    try:
        command(ctl, "demo.inject_mismatch")
        submit(ctl, "physician", "en-CA", DOSE)
        injected = drain_until(ctl, "turn.result")[-1]["payload"]["turnId"]
        command(ctl, "visit.mark_high_risk", turnId=injected, note="dose")
        drain_until(tv, "interpreter.escalation")
        command(ctl, "demo.inject_mismatch")
        drain_until(ctl, "demo.injection_state")
        with client.websocket_connect("/ws/visit?role=controller") as again:
            state = again.receive_json()["payload"]
            assert state["injection"] == {"state": "armed", "injectedTurnIds": [injected]}
            assert [(e["action"], e["reason"], e["turnId"], e["note"]) for e in state["escalations"]] == [
                ("mark", "high_risk", injected, "dose")
            ]
            assert state["interpreterOpen"] is True
        for role in ("screen", "review"):
            with client.websocket_connect(f"/ws/visit?role={role}") as late:
                state = late.receive_json()["payload"]
                assert not {"injection", "escalations"} & state.keys()
                assert "inject" not in str(state).lower()
    finally:
        close(sockets)
