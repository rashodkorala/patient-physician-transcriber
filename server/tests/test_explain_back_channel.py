"""Explain-back on the visit channel (CDR-005, ADR-011, demo-night-mvp task 3.4): the bracketed mode, its refusals,
code-decided outcomes, the private result, the content-free state, and the chain entry."""

import pytest
from test_visit_channel import (
    drain_until,
    give_consent,
    kb,  # noqa: F401  (fixture)
    make_client,
    submit,
    types,
    withdraw_consent,
)
from visit_helpers import (
    CHEST,
    SAID_DOSE_ONLY,
    SAID_IN_FULL,
    SAID_ONCE_A_DAY,
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

from chains.explain_back import ExplainBackDraft
from fake_model import TONE_MARKER


@pytest.fixture
def client(kb):  # noqa: F811
    with make_client(kb, translate=translate) as c:
        yield c


def start(ctl) -> str:
    command(ctl, "explainback.start")
    state = drain_until(ctl, "explainback.state")[-1]["payload"]
    assert state["state"] == "listening" and state["explanationTurnIds"] == []
    return state["explainBackId"]


def check(ctl, explain_back_id):
    command(ctl, "explainback.check", explainBackId=explain_back_id)
    events = drain_until(ctl, "explainback.result")
    return events, events[-1]["payload"]


def code_item(result, kind):
    return next(i for i in result["items"] if i["kind"] == kind and i["decidedBy"] == "code")


def test_missed_frequency_is_flagged_by_code_even_when_the_model_says_matched_cdr_005(client):
    sockets, (ctl, tv, phone) = connect(client, "controller", "screen", "review")
    try:
        plan_turn = speak_plan(ctl)
        explain_back_id = start(ctl)
        said = patient_says(ctl, SAID_DOSE_ONLY)
        state = drain_until(ctl, "explainback.state")[-1]["payload"]
        assert state["explanationTurnIds"] == [said["turnId"]]

        events, result = check(ctl, explain_back_id)
        states = [e["payload"]["state"] for e in events if e["type"] == "explainback.state"]
        assert states == ["checking"]
        assert result["explainBackId"] == result["entryId"] == explain_back_id
        assert result["explanationTurnIds"] == [said["turnId"]]
        frequency = code_item(result, "frequency")
        assert frequency["outcome"] == "missed" and frequency["sourceTurnIds"] == [plan_turn]
        # The fake model judges every code item matched; code's outcome stands (ADR-011).
        assert code_item(result, "dose")["outcome"] == "matched"
        assert drain_until(ctl, "explainback.state")[-1]["payload"]["state"] == "done"

        # Every other role sees only the content-free state, never the result.
        _, (tv_events, phone_events) = marker(ctl, tv, phone)
        for seen in (tv_events, phone_events):
            assert_public(seen)
            done = [e["payload"] for e in seen if e["type"] == "explainback.state"]
            assert [s["state"] for s in done][-1] == "done"
            assert all(set(s) == {"explainBackId", "state", "explanationTurnIds"} for s in done)
    finally:
        close(sockets)


def test_a_different_frequency_is_contradicted_cdr_005(client):
    sockets, (ctl,) = connect(client, "controller")
    try:
        speak_plan(ctl)
        explain_back_id = start(ctl)
        patient_says(ctl, SAID_ONCE_A_DAY)
        _, result = check(ctl, explain_back_id)
        frequency = code_item(result, "frequency")
        assert frequency["outcome"] == "contradicted" and frequency["heard"] == "1 times per day"
    finally:
        close(sockets)


def test_the_result_is_chained_and_kept_for_the_controller_only_cdr_005_cdr_006(client):
    sockets, (ctl,) = connect(client, "controller")
    try:
        speak_plan(ctl)
        explain_back_id = start(ctl)
        patient_says(ctl, SAID_IN_FULL)
        _, result = check(ctl, explain_back_id)
        drain_until(ctl, "record.integrity")
        entry = entries(client)[-1]
        assert entry["kind"] == "explain_back" and entry["entryId"] == explain_back_id
        assert entry["body"] == {k: v for k, v in result.items() if k != "entryId"}
        assert all(i["outcome"] == "matched" for i in result["items"] if i["decidedBy"] == "code")
    finally:
        close(sockets)
    with client.websocket_connect("/ws/visit?role=controller") as ctl:
        state = ctl.receive_json()["payload"]
        assert state["explainBack"]["state"] == "done" and state["explainBackResults"] == [result]
    for role in ("screen", "review"):
        with client.websocket_connect(f"/ws/visit?role={role}") as ws:
            snapshot = ws.receive_json()
            assert_public([snapshot])
            assert snapshot["payload"]["explainBack"]["state"] == "done"


def test_a_screen_connecting_mid_explain_back_gets_state_only_cdr_005(client):
    sockets, (ctl,) = connect(client, "controller")
    try:
        speak_plan(ctl)
        explain_back_id = start(ctl)
        said = patient_says(ctl, SAID_DOSE_ONLY)
        drain_until(ctl, "explainback.state")
        with client.websocket_connect("/ws/visit?role=screen") as tv:
            snapshot = tv.receive_json()
            assert snapshot["payload"]["explainBack"] == {
                "explainBackId": explain_back_id,
                "state": "listening",
                "explanationTurnIds": [said["turnId"]],
            }
            assert_public([snapshot])
    finally:
        close(sockets)


def test_physician_blocked_and_escalated_turns_never_join_the_explanation_cdr_005(kb):  # noqa: F811
    with make_client(kb, translate=translate) as client:
        sockets, (ctl,) = connect(client, "controller")
        try:
            speak_plan(ctl)
            explain_back_id = start(ctl)
            submit(ctl, "physician", "en-CA", "Any questions?")
            drain_until(ctl, "turn.result")
            submit(ctl, "patient", "pa-IN", f"ਠੀਕ ਹੈ {TONE_MARKER}")
            escalated = drain_until(ctl, "turn.result")[-1]["payload"]
            assert escalated["status"] == "escalated"
            submit(ctl, "patient", "pa-IN", "(test: mismatch) 500 ਮਿਲੀਗ੍ਰਾਮ")
            blocked = drain_until(ctl, "turn.result")[-1]["payload"]
            assert blocked["status"] == "blocked"
            said = patient_says(ctl, SAID_DOSE_ONLY)
            _, result = check(ctl, explain_back_id)
            assert result["explanationTurnIds"] == [said["turnId"]]
        finally:
            close(sockets)


def test_start_is_refused_without_consent_while_paused_during_readback_with_no_plan_and_when_open_cdr_005(kb):  # noqa: F811
    with make_client(kb, translate=translate, consent=False) as client:
        sockets, (ctl,) = connect(client, "controller")
        try:

            def refused(message_part=None):
                command(ctl, "explainback.start")
                error = drain_until(ctl, "error")[-1]["payload"]
                assert error["command"] == "explainback.start"
                if message_part:
                    assert message_part in error["message"]

            refused("Consent")
            give_consent(ctl)
            drain_until(ctl, "consent.changed")
            refused("Explain the plan")  # nothing spoken by the physician yet
            patient_says(ctl, CHEST)
            refused("Explain the plan")  # a patient turn is not a plan
            submit(ctl, "physician", "en-CA", "Take metformin 500 milligrams twice a day.")
            turn_id = drain_until(ctl, "turn.readback_required")[-1]["payload"]["turnId"]
            refused("dose")  # a read-back is pending
            command(ctl, "turn.readback_confirm", turnId=turn_id)
            drain_until(ctl, "turn.result")
            command(ctl, "visit.pause")
            drain_until(ctl, "visit.paused")
            refused("Paused")
            command(ctl, "visit.resume")
            drain_until(ctl, "visit.resumed")
            start(ctl)
            refused("already open")
        finally:
            close(sockets)


def test_check_and_cancel_rules_cdr_005(client):
    sockets, (ctl,) = connect(client, "controller")
    try:
        speak_plan(ctl)
        explain_back_id = start(ctl)
        command(ctl, "explainback.check", explainBackId=explain_back_id)
        assert "not explained" in drain_until(ctl, "error")[-1]["payload"]["message"]  # nothing said back yet
        command(ctl, "explainback.check", explainBackId="nope")
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "explainback.check"
        command(ctl, "explainback.cancel", explainBackId=explain_back_id)
        assert drain_until(ctl, "explainback.state")[-1]["payload"]["state"] == "cancelled"
        command(ctl, "explainback.cancel", explainBackId=explain_back_id)
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "explainback.cancel"
        patient_says(ctl, SAID_DOSE_ONLY)  # after cancel, turns no longer join anything
        assert visit(client).explain_back.explanation_turn_ids == []
        assert "explain_back" not in kinds(client)
        start(ctl)  # a new one can open
    finally:
        close(sockets)


@pytest.mark.parametrize("role", ["screen", "review"])
def test_explain_back_commands_are_dropped_from_other_roles_cdr_005(client, role):
    sockets, (ctl, other) = connect(client, "controller", role)
    try:
        speak_plan(ctl)
        drain_until(other, "turn.result")
        command(other, "explainback.start")
        _, (seen,) = marker(ctl, other)
        assert "explainback.state" not in types(seen) and "command.refused" not in types(seen)
        assert visit(client).explain_back is None
    finally:
        close(sockets)


def test_withdrawal_cancels_an_open_explain_back_cdr_005(client):
    sockets, (ctl,) = connect(client, "controller")
    try:
        speak_plan(ctl)
        start(ctl)
        withdraw_consent(ctl)
        assert drain_until(ctl, "explainback.state")[-1]["payload"]["state"] == "cancelled"
    finally:
        close(sockets)


def test_a_failing_model_fails_the_check_with_nothing_chained_cdr_005(kb):  # noqa: F811
    def no_evidence(user):
        # An item claimed matched with no evidence fails ADR-011's checks on both attempts.
        from chains.explain_back import DraftItem

        item = DraftItem(
            kind="instruction", instruction="Rest", source_turn_ids=["x"], outcome="matched", evidence_turn_ids=[]
        )
        return ExplainBackDraft(items=[item], code_item_views=[])

    with make_client(kb, translate=translate, handlers={"explain_back": no_evidence}) as client:
        sockets, (ctl, tv) = connect(client, "controller", "screen")
        try:
            speak_plan(ctl)
            explain_back_id = start(ctl)
            patient_says(ctl, SAID_DOSE_ONLY)
            command(ctl, "explainback.check", explainBackId=explain_back_id)
            events = drain_until(ctl, "error")
            assert "explain-back check failed" in events[-1]["payload"]["message"]
            assert [e["payload"]["state"] for e in events if e["type"] == "explainback.state"][-1] == "failed"
            assert "explainback.result" not in types(events)
            assert "explain_back" not in kinds(client)
            _, (tv_events,) = marker(ctl, tv)
            assert_public(tv_events)
        finally:
            close(sockets)
