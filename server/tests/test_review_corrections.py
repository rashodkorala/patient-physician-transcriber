"""Review corrections, confirmations, and the tamper control on the visit channel (CDR-006, TDM-005, IDR-003,
demo-night-mvp tasks 3.5 and 3.8): append-only history, the same turn graph rules as a live turn, refusals, and
role rules."""

import pytest
from test_visit_channel import (
    drain_until,
    kb,  # noqa: F401  (fixture)
    make_client,
    submit,
    types,
)
from visit_helpers import (
    CHEST,
    CHEST_CORRECTED,
    assert_public,
    close,
    command,
    connect,
    entries,
    kinds,
    marker,
    patient_says,
    speak_plan,
    translate,
    visit,
)

from fake_model import MISMATCH_MARKER, TONE_MARKER
from visit_store import TAMPER_MARK


@pytest.fixture
def client(kb):  # noqa: F811
    with make_client(kb, translate=translate) as c:
        yield c


def amend(ws, segment_id, text, language="pa-IN", confidence=0.9):
    command(ws, "segment.amend", segmentId=segment_id, text=text, language=language, recognitionConfidence=confidence)


def until_outcome(ws):
    """Events up to a correction's applied or refused segment.status."""
    seen = []
    while True:
        event = ws.receive_json()
        seen.append(event)
        if event["type"] == "segment.status" and event["payload"]["stage"] in ("applied", "refused"):
            return seen


def refused(ws, command_name):
    event = drain_until(ws, "command.refused")[-1]["payload"]
    assert event["command"] == command_name
    return event["reason"]


# ---------- corrections ----------


def test_amendment_keeps_original_cdr_006(client):
    sockets, (ctl, tv, phone) = connect(client, "controller", "screen", "review")
    try:
        turn = patient_says(ctl, CHEST)
        segment_id = turn["turnId"]
        drain_until(phone, "turn.result")
        original_entry = next(e for e in visit(client).chain.entries if e.payload["entryId"] == segment_id)

        amend(phone, segment_id, CHEST_CORRECTED[0])
        phone_events = until_outcome(phone)
        stages = [e["payload"]["stage"] for e in phone_events if e["type"] == "segment.status"]
        assert stages[0] == "translating" and "verifying" in stages and stages[-1] == "applied"
        amended = next(e["payload"] for e in phone_events if e["type"] == "segment.amended")
        amendment_id = amended["amendmentId"]
        assert amended == {
            "segmentId": segment_id,
            "by": "patient",
            "action": "amend",
            "newText": CHEST_CORRECTED[0],
            "amendmentId": amendment_id,
            "version": None,
            "translation": CHEST_CORRECTED[1],
            "toneLabel": "respectful",
            "criticalValues": [],
            "entryId": amendment_id,
        }
        assert_public(phone_events)

        ctl_events = until_outcome(ctl)
        analysis = next(e["payload"] for e in ctl_events if e["type"] == "segment.analysis")
        assert analysis["segmentId"] == segment_id and analysis["result"]["turnId"] == amendment_id
        assert analysis["result"]["status"] == "final"
        _, (tv_events,) = marker(ctl, tv)
        assert_public(tv_events)

        # One amendment entry; the original turn entry and its hash are untouched; the record still verifies.
        assert kinds(client)[-1] == "amendment"
        entry = entries(client)[-1]
        assert entry["entryId"] == amendment_id and entry["body"]["replaces"] == "original"
        assert entry["body"]["segmentId"] == segment_id and entry["body"]["by"] == "patient"
        assert next(e for e in visit(client).chain.entries if e.payload["entryId"] == segment_id) == original_entry
        assert visit(client).integrity().status == "verified"
    finally:
        close(sockets)

    # History: the original first, then the correction, for every role; only the controller sees the analysis.
    for role in ("controller", "screen", "review"):
        with client.websocket_connect(f"/ws/visit?role={role}") as ws:
            state = ws.receive_json()["payload"]
            (history,) = state["segments"]
            assert history["original"]["sourceText"] == CHEST[0]
            assert history["original"]["translation"] == CHEST[1]
            assert [a["sourceText"] for a in history["amendments"]] == [CHEST_CORRECTED[0]]
            assert history["current"] == amendment_id and history["confirmed"] is None
            # The existing turns keep the original unchanged.
            assert state["turns"][0]["sourceText"] == CHEST[0]
            if role == "controller":
                assert history["amendments"][0]["analysis"]["turnId"] == amendment_id
            else:
                assert_public([{"type": "visit.state", "payload": state}])


@pytest.mark.parametrize(("marker_text", "reason"), [(MISMATCH_MARKER, "blocked"), (TONE_MARKER, "escalated")])
def test_a_blocked_or_escalated_correction_is_refused_and_unrecorded_cdr_006(client, marker_text, reason):
    sockets, (ctl, tv, phone) = connect(client, "controller", "screen", "review")
    try:
        segment_id = patient_says(ctl, CHEST)["turnId"]
        drain_until(phone, "turn.result")
        before = list(visit(client).chain.entries)
        amend(phone, segment_id, f"ਮੈਟਫਾਰਮਿਨ 500 ਮਿਲੀਗ੍ਰਾਮ {marker_text}")
        phone_events = until_outcome(phone)
        assert phone_events[-1]["payload"]["reason"] == reason
        assert "segment.amended" not in types(phone_events)
        assert_public(phone_events)
        ctl_events = until_outcome(ctl)
        analysis = next(e["payload"] for e in ctl_events if e["type"] == "segment.analysis")
        assert analysis["result"]["status"] == reason
        assert "interpreter.escalation" not in types(ctl_events)  # an offer would be chained; this is not
        _, (tv_events,) = marker(ctl, tv)
        assert_public(tv_events)
        assert list(visit(client).chain.entries) == before
        assert visit(client).segments == {} and visit(client).amend_in_flight is None
    finally:
        close(sockets)


def test_segment_amend_refusals_cdr_006(client):
    sockets, (ctl, tv, phone) = connect(client, "controller", "screen", "review")
    try:
        plan = speak_plan(ctl)
        patient = patient_says(ctl, CHEST)["turnId"]
        submit(ctl, "patient", "pa-IN", f"ਦਰਦ {TONE_MARKER}")
        escalated = drain_until(ctl, "turn.result")[-1]["payload"]["turnId"]
        drain_until(phone, "record.integrity")

        amend(phone, plan, "x")
        assert refused(phone, "segment.amend") == "not_allowed"  # a physician turn
        amend(phone, escalated, "x")
        assert refused(phone, "segment.amend") == "not_allowed"  # an escalated turn
        amend(phone, "nope", "x")
        assert refused(phone, "segment.amend") == "not_found"
        amend(phone, patient, "Bonjour", language="fr-CA")
        assert refused(phone, "segment.amend") == "wrong_language"
        amend(phone, patient, "   ")
        assert refused(phone, "segment.amend") == "invalid"
        visit(client).amend_in_flight = "other"
        amend(phone, patient, CHEST_CORRECTED[0])
        assert refused(phone, "segment.amend") == "busy"
        visit(client).amend_in_flight = None
        command(ctl, "visit.pause")
        drain_until(phone, "visit.paused")
        amend(phone, patient, CHEST_CORRECTED[0])
        assert refused(phone, "segment.amend") == "not_allowed"
        command(ctl, "visit.resume")
        drain_until(phone, "visit.resumed")

        # From the controller: refused with `error`. From the screen: nothing comes back.
        amend(ctl, patient, CHEST_CORRECTED[0])
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "segment.amend"
        amend(tv, patient, CHEST_CORRECTED[0])
        _, (tv_events, phone_events) = marker(ctl, tv, phone)
        assert not {"error", "command.refused", "segment.status"} & set(types(tv_events))
        assert "error" not in types(phone_events)
        assert "amendment" not in kinds(client)
    finally:
        close(sockets)


def test_segment_amend_waits_for_consent_cdr_005_cdr_006(client):
    sockets, (ctl, phone) = connect(client, "controller", "review")
    try:
        segment_id = patient_says(ctl, CHEST)["turnId"]
        command(ctl, "consent.withdraw")
        drain_until(phone, "consent.changed")
        amend(phone, segment_id, CHEST_CORRECTED[0])
        assert refused(phone, "segment.amend") == "consent_required"
    finally:
        close(sockets)


# ---------- confirmations ----------


def test_confirmations_name_their_version_and_are_chained_cdr_006(client):
    sockets, (ctl, phone) = connect(client, "controller", "review")
    try:
        segment_id = patient_says(ctl, CHEST)["turnId"]
        drain_until(phone, "turn.result")
        command(phone, "segment.confirm", segmentId=segment_id, version="original")
        confirmed = drain_until(phone, "segment.amended")[-1]["payload"]
        assert confirmed["action"] == "confirm" and confirmed["version"] == "original"
        entry = entries(client)[-1]
        assert entry["kind"] == "confirmation" and entry["entryId"] == confirmed["entryId"]
        assert entry["body"] == {"segmentId": segment_id, "version": "original", "by": "patient"}

        command(phone, "segment.confirm", segmentId=segment_id, version="original")
        assert refused(phone, "segment.confirm") == "not_allowed"  # already confirmed

        amend(phone, segment_id, CHEST_CORRECTED[0])
        amendment_id = next(e for e in until_outcome(phone) if e["type"] == "segment.amended")["payload"]["amendmentId"]
        command(phone, "segment.confirm", segmentId=segment_id, version="original")
        assert refused(phone, "segment.confirm") == "not_current"
        command(phone, "segment.confirm", segmentId=segment_id, version=amendment_id)
        assert drain_until(phone, "segment.amended")[-1]["payload"]["version"] == amendment_id
        assert kinds(client)[-3:] == ["confirmation", "amendment", "confirmation"]

        command(ctl, "segment.confirm", segmentId=segment_id, version=amendment_id)
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "segment.confirm"
    finally:
        close(sockets)
    with client.websocket_connect("/ws/visit?role=review") as phone:
        (history,) = phone.receive_json()["payload"]["segments"]
        assert history["confirmed"]["version"] == amendment_id and history["current"] == amendment_id


# ---------- the tamper control (TDM-005) ----------


def tamper(ws, entry_id):
    command(ws, "demo.tamper_record", entryId=entry_id)


def until_broken(ws):
    """Events up to the first record.integrity that reports the record broken."""
    seen = []
    while True:
        event = ws.receive_json()
        seen.append(event)
        if event["type"] == "record.integrity" and event["payload"]["status"] == "broken":
            return seen


def test_tamper_breaks_the_record_at_the_altered_turn_cdr_006_tdm_005(client):
    sockets, (ctl, tv, phone) = connect(client, "controller", "screen", "review")
    try:
        first = patient_says(ctl, CHEST)["turnId"]
        speak_plan(ctl)
        drain_until(tv, "record.integrity")
        assert visit(client).integrity().status == "verified"

        tamper(ctl, first)
        state = drain_until(ctl, "demo.tamper_state")[-1]["payload"]
        assert state["entryId"] == first
        integrity = drain_until(ctl, "record.integrity")[-1]["payload"]
        assert integrity["status"] == "broken" and integrity["brokenAt"] == first
        stored = next(e.payload for e in visit(client).chain.entries if e.payload["entryId"] == first)
        assert stored["body"]["sourceText"] == CHEST[0] + TAMPER_MARK

        for ws in (tv, phone):
            seen = until_broken(ws)
            assert seen[-1]["payload"]["brokenAt"] == first
            assert_public(seen)
            assert "tamper" not in str(seen).lower()

        tamper(ctl, first)
        assert "already been used" in drain_until(ctl, "error")[-1]["payload"]["message"]
    finally:
        close(sockets)
    with client.websocket_connect("/ws/visit?role=controller") as ctl:
        assert ctl.receive_json()["payload"]["tamper"]["entryId"] == first
    for role in ("screen", "review"):
        with client.websocket_connect(f"/ws/visit?role={role}") as ws:
            snapshot = ws.receive_json()
            assert snapshot["payload"]["integrity"]["brokenAt"] == first
            assert "tamper" not in snapshot["payload"]


def test_altering_an_amendment_names_its_amendment_id_cdr_006(client):
    sockets, (ctl, phone) = connect(client, "controller", "review")
    try:
        segment_id = patient_says(ctl, CHEST)["turnId"]
        drain_until(phone, "turn.result")
        amend(phone, segment_id, CHEST_CORRECTED[0])
        amendment_id = next(e for e in until_outcome(phone) if e["type"] == "segment.amended")["payload"]["amendmentId"]
        tamper(ctl, amendment_id)
        assert until_broken(ctl)[-1]["payload"]["brokenAt"] == amendment_id
    finally:
        close(sockets)


def test_tamper_refuses_other_entry_kinds_and_unknown_ids_tdm_005(client):
    sockets, (ctl,) = connect(client, "controller")
    try:
        consent_id = visit(client).consent_state.entry_id
        tamper(ctl, consent_id)
        assert "Only a turn" in drain_until(ctl, "error")[-1]["payload"]["message"]
        tamper(ctl, "nope")
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "demo.tamper_record"
        assert visit(client).tamper is None and visit(client).integrity().status == "verified"
    finally:
        close(sockets)


@pytest.mark.parametrize("role", ["screen", "review"])
def test_tamper_is_dropped_from_screen_and_review_tdm_005(client, role):
    sockets, (ctl, other) = connect(client, "controller", role)
    try:
        segment_id = patient_says(ctl, CHEST)["turnId"]
        tamper(other, segment_id)
        _, (seen,) = marker(ctl, other)
        assert not {"command.refused", "error", "demo.tamper_state"} & set(types(seen))
        assert visit(client).tamper is None and visit(client).integrity().status == "verified"
    finally:
        close(sockets)


# ---------- task 5.2: the injected turn on the review screen ----------


def test_review_sees_the_injected_turn_blocked_then_repeated_without_injection_state_tdm_002(client):
    sockets, (ctl, phone) = connect(client, "controller", "review")
    try:
        command(ctl, "demo.inject_mismatch")
        submit(ctl, "physician", "en-CA", "Take metformin 500 milligrams twice a day.")
        blocked = drain_until(phone, "turn.result")
        assert blocked[-1]["payload"]["status"] == "blocked" and blocked[-1]["payload"]["translation"] is None
        speak_plan(ctl)
        repeated = drain_until(phone, "turn.result")
        assert repeated[-1]["payload"]["status"] == "final"
        assert_public(blocked + repeated)
        assert "demo.injection_state" not in types(blocked + repeated)
    finally:
        close(sockets)
