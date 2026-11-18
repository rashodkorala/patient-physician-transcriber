"""Consent on the visit channel (CDR-005, demo-night-mvp task 3.2): the server-held gate, who gave consent, the
language lock, withdrawal, the notice read aloud through the speak gate, and refusals to the review screen."""

import asyncio
import hashlib

import pytest
from test_visit_channel import (
    DOSE,
    SETTINGS,
    ConsentedClient,
    contains_private,
    drain_until,
    drain_until_stage,
    give_consent,
    kb,  # noqa: F401  (fixture)
    make_client,
    set_languages,
    set_names,
    submit,
    types,
    withdraw_consent,
)
from test_voice import FakeVoice

import fake_model
from hash_chain import canonical_json
from introduction import CONSENT_NOTICES, load_consent_notices
from llm import ScriptedModel
from main import CONSENT_NEEDED, create_app

PA = CONSENT_NOTICES["pa-IN"]


@pytest.fixture
def client(kb):  # noqa: F811
    with make_client(kb, consent=False) as c:
        yield c


def command(ws, type_, **payload):
    ws.send_json({"type": type_, "payload": payload})


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


def consent_entries(client):
    return [e.payload for e in client.app.state.hub.visit.chain.entries if e.payload["kind"] == "consent"]


# ---------- the notices ----------


def test_every_patient_language_has_a_notice_in_its_language_and_english_cdr_005():
    assert set(CONSENT_NOTICES) == {"pa-IN", "fr-CA", "ta-LK", "si-LK"}
    for language, notice in CONSENT_NOTICES.items():
        assert notice.notice_id == f"{language}-v{notice.version}"
        assert notice.speech_id == f"consent-{notice.notice_id}" and len(notice.speech_id) <= 64
        assert [line.language for line in notice.lines] == [language, "en-CA"]
        assert all(line.text and "\n" not in line.text for line in notice.lines)


def test_a_notice_written_against_other_english_fails_at_start_up_cdr_005(tmp_path):
    (tmp_path / "en-CA.yaml").write_text('language: en-CA\nversion: "2"\ntext: Hello\n', encoding="utf-8")
    (tmp_path / "pa-IN.yaml").write_text(
        'language: pa-IN\nversion: "1"\nenglish_version: "1"\ntext: ਸਤ ਸ੍ਰੀ ਅਕਾਲ\n', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="English"):
        load_consent_notices(tmp_path)


def test_every_role_sees_the_notice_and_no_consent_before_it_is_given_cdr_005(client):
    sockets = [client.websocket_connect(f"/ws/visit?role={role}") for role in ("controller", "screen", "review")]
    try:
        states = [s.__enter__().receive_json()["payload"] for s in sockets]
        for state in states:
            assert state["consent"] is None and state["consentState"] is None
            assert state["consentNotice"] == PA.wire()
    finally:
        for s in reversed(sockets):
            s.__exit__(None, None, None)


# ---------- the gate ----------


def test_consent_blocks_turns_cdr_005(client):
    sockets, (ctl, tv) = connect(client, "controller", "screen")
    try:
        for type_, payload in [
            (
                "turn.submit",
                {"speaker": "patient", "language": "pa-IN", "text": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ", "recognitionConfidence": 1},
            ),
            ("visit.start_introduction", {}),
            ("visit.name_reply", {"role": "physician", "text": "I'm Dr. Thomas"}),
        ]:
            ctl.send_json({"type": type_, "payload": payload})
            error = drain_until(ctl, "error")[-1]["payload"]
            assert error == {"message": CONSENT_NEEDED, "command": type_}
        _, (tv_events,) = marker(ctl, tv)
        assert "turn.started" not in types(tv_events) and "interpreter.line" not in types(tv_events)
        assert client.app.state.hub.visit.turns == {}

        give_consent(ctl)
        drain_until(ctl, "consent.changed")
        command(ctl, "visit.start_introduction")
        assert drain_until(tv, "interpreter.line")[-1]["payload"]["purpose"] == "introduction"
        submit(ctl, "patient", "pa-IN", "ਸਤ ਸ੍ਰੀ ਅਕਾਲ")
        assert drain_until(tv, "turn.result")[-1]["payload"]["sourceText"] == "ਸਤ ਸ੍ਰੀ ਅਕਾਲ"
    finally:
        close(sockets)


def test_name_reply_is_accepted_after_consent_cdr_005(client):
    sockets, (ctl,) = connect(client, "controller")
    try:
        give_consent(ctl)
        drain_until(ctl, "consent.changed")
        command(ctl, "visit.start_introduction")
        drain_until(ctl, "interpreter.line")
        command(ctl, "visit.name_reply", role="physician", text="I'm Dr. Thomas")
        assert drain_until(ctl, "visit.name_proposed")[-1]["payload"] == {"role": "physician", "name": "Dr. Thomas"}
    finally:
        close(sockets)


def test_setup_stays_allowed_before_consent_cdr_005(client):
    sockets, (ctl,) = connect(client, "controller")
    try:
        set_names(ctl, physicianName="Dr. Thomas")
        assert drain_until(ctl, "visit.names")[-1]["payload"]["physicianName"] == "Dr. Thomas"
        set_languages(ctl, "fr-CA")
        assert drain_until(ctl, "visit.state")[-1]["payload"]["consentNotice"]["noticeId"] == "fr-CA-v1"
    finally:
        close(sockets)


# ---------- giving consent ----------


def test_consent_from_the_controller_is_physician_on_behalf_and_chained_cdr_005(client):
    sockets, (ctl, tv) = connect(client, "controller", "screen")
    try:
        give_consent(ctl)
        state = drain_until(tv, "consent.changed")[-1]["payload"]
        assert state["state"] == "given" and state["by"] == "physician_on_behalf"
        assert (state["noticeId"], state["noticeVersion"], state["language"]) == ("pa-IN-v1", "1", "pa-IN")
        integrity = drain_until(tv, "record.integrity")[-1]["payload"]
        visit = client.app.state.hub.visit
        assert integrity == {"status": "verified", "headHash": visit.chain.head_hash, "brokenAt": None}
        (entry,) = consent_entries(client)
        assert entry["entryId"] == state["entryId"] and entry["at"] == state["at"] == visit.consent
        expected_sha = hashlib.sha256(canonical_json([line.wire() for line in PA.lines])).hexdigest()
        assert entry["body"] == {
            "state": "given",
            "at": state["at"],
            "by": "physician_on_behalf",
            "noticeId": "pa-IN-v1",
            "noticeVersion": "1",
            "language": "pa-IN",
            "noticeSha256": expected_sha,
            "reason": None,
        }
        with client.websocket_connect("/ws/visit?role=screen") as late:
            snapshot = late.receive_json()["payload"]
            assert snapshot["consent"] == state["at"] and snapshot["consentState"] == state
    finally:
        close(sockets)


def test_consent_from_the_review_screen_is_the_patients_cdr_005(client):
    sockets, (ctl, phone) = connect(client, "controller", "review")
    try:
        give_consent(phone)
        assert drain_until(ctl, "consent.changed")[-1]["payload"]["by"] == "patient"
        assert drain_until(phone, "consent.changed")[-1]["payload"]["by"] == "patient"
        assert consent_entries(client)[0]["body"]["by"] == "patient"
    finally:
        close(sockets)


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        ({"noticeVersion": "1", "language": "fr-CA"}, "wrong_language"),
        ({"noticeVersion": "0", "language": "pa-IN"}, "wrong_notice"),
        ({"noticeVersion": "2", "language": "pa-IN"}, "wrong_notice"),
    ],
)
def test_consent_give_is_refused_for_a_wrong_language_or_stale_notice_cdr_005(client, payload, reason):
    sockets, (ctl, phone) = connect(client, "controller", "review")
    try:
        ctl.send_json({"type": "consent.give", "payload": payload})
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "consent.give"
        phone.send_json({"type": "consent.give", "payload": payload})
        refused = phone.receive_json()
        assert refused["type"] == "command.refused"
        assert refused["payload"] == {"command": "consent.give", "reason": reason}
        assert client.app.state.hub.visit.consent is None and consent_entries(client) == []
    finally:
        close(sockets)


def test_a_second_give_is_refused_cdr_005(client):
    sockets, (ctl, phone) = connect(client, "controller", "review")
    try:
        give_consent(ctl)
        drain_until(phone, "record.integrity")
        give_consent(phone)
        assert drain_until(phone, "command.refused")[-1]["payload"]["reason"] == "consent_already_given"
        give_consent(ctl)
        assert drain_until(ctl, "error")[-1]["payload"]["message"] == "Consent is already given"
        assert len(consent_entries(client)) == 1
    finally:
        close(sockets)


def test_a_screen_cannot_give_withdraw_or_read_consent_cdr_005(client):
    sockets, (ctl, tv) = connect(client, "controller", "screen")
    try:
        give_consent(tv)
        command(tv, "consent.read_aloud")
        ctl_events, (tv_events,) = marker(ctl, tv)
        assert not {"consent.changed", "consent.speak", "command.refused", "error"} & set(types(ctl_events + tv_events))
        assert client.app.state.hub.visit.consent is None
        give_consent(ctl)
        drain_until(ctl, "consent.changed")
        withdraw_consent(tv)
        marker(ctl, tv)
        assert client.app.state.hub.visit.consent is not None
    finally:
        close(sockets)


def test_a_review_connection_gets_command_refused_and_never_error_cdr_005(client):
    sockets, (ctl, phone) = connect(client, "controller", "review")
    try:
        withdraw_consent(phone)
        assert phone.receive_json()["payload"] == {"command": "consent.withdraw", "reason": "consent_not_given"}
        phone.send_json({"type": "consent.give", "payload": {"noticeVersion": 1}})
        assert phone.receive_json()["payload"] == {"command": "consent.give", "reason": "invalid"}
        command(phone, "visit.resume")  # not paused
        assert phone.receive_json()["payload"] == {"command": "visit.resume", "reason": "invalid"}
        command(phone, "no.such.command")
        assert phone.receive_json()["type"] == "command.refused"
        _, (phone_events,) = marker(ctl, phone)
        assert "error" not in types(phone_events)
    finally:
        close(sockets)


# ---------- the language lock ----------


def test_languages_lock_with_consent_and_unlock_on_withdrawal_cdr_005(client):
    sockets, (ctl, tv) = connect(client, "controller", "screen")
    try:
        give_consent(ctl)
        drain_until(ctl, "consent.changed")
        drain_until(tv, "consent.changed")
        set_languages(ctl, "fr-CA")
        error = drain_until(ctl, "error")[-1]["payload"]
        assert error["command"] == "visit.set_languages" and "Withdraw consent" in error["message"]
        assert client.app.state.hub.visit.patient_language == "pa-IN"
        withdraw_consent(ctl, reason="  Wrong   language  ")
        state = drain_until(tv, "consent.changed")[-1]["payload"]
        assert state["state"] == "withdrawn" and state["by"] == "physician_on_behalf"
        assert consent_entries(client)[-1]["body"]["reason"] == "Wrong language"
        set_languages(ctl, "fr-CA")
        snapshot = drain_until(ctl, "visit.state")[-1]["payload"]
        assert snapshot["patientLanguage"] == "fr-CA" and snapshot["consent"] is None
        assert snapshot["consentNotice"]["noticeId"] == "fr-CA-v1"
        # Consent can be given again, to the new notice, and every earlier entry stays.
        ctl.send_json({"type": "consent.give", "payload": {"noticeVersion": "1", "language": "fr-CA"}})
        drain_until(ctl, "consent.changed")
        assert [e["body"]["state"] for e in consent_entries(client)] == ["given", "withdrawn", "given"]
        assert [e["body"]["noticeId"] for e in consent_entries(client)] == ["pa-IN-v1", "pa-IN-v1", "fr-CA-v1"]
    finally:
        close(sockets)


# ---------- withdrawal stops capture ----------


def test_withdrawal_blocks_turns_again_and_keeps_settled_turns_cdr_005(kb):  # noqa: F811
    with make_client(kb) as client:
        sockets, (ctl, tv) = connect(client, "controller", "screen")
        try:
            submit(ctl, "physician", "en-CA", "Hello.")
            turn_id = drain_until(tv, "turn.result")[-1]["payload"]["turnId"]
            withdraw_consent(ctl)
            drain_until(ctl, "consent.changed")
            submit(ctl, "physician", "en-CA", "Next.")
            assert drain_until(ctl, "error")[-1]["payload"]["message"] == CONSENT_NEEDED
            with client.websocket_connect("/ws/visit?role=screen") as late:
                assert [t["turnId"] for t in late.receive_json()["payload"]["turns"]] == [turn_id]
        finally:
            close(sockets)


def test_withdrawal_during_a_readback_discards_it_unspoken_cdr_005(kb):  # noqa: F811
    with make_client(kb, voice=FakeVoice()) as client:
        sockets, (ctl, tv) = connect(client, "controller", "screen")
        try:
            submit(ctl, "physician", "en-CA", DOSE)
            turn_id = drain_until_stage(ctl, "awaiting_readback")[-1]["payload"]["turnId"]
            withdraw_consent(ctl)
            events = drain_until_stage(tv, "discarded")
            assert "consent.changed" in types(events) and "turn.result" not in types(events)
            assert client.app.state.hub.visit.pending_readback is None
            ctl.send_json({"type": "turn.readback_confirm", "payload": {"turnId": turn_id}})
            assert drain_until(ctl, "error")[-1]["payload"]["command"] == "turn.readback_confirm"
            assert client.get(f"/api/speech/{turn_id}").status_code == 404
            assert all(e.payload["kind"] == "consent" for e in client.app.state.hub.visit.chain.entries)
        finally:
            close(sockets)


class HeldModel(ScriptedModel):
    """Holds every translation until consent is withdrawn, so the withdrawal lands while the turn is in the graph."""

    app = None

    async def parse(self, *, purpose, system, user, schema):
        if purpose == "translate":
            while self.app.state.hub.visit.consent is not None:
                await asyncio.sleep(0.01)
        return await super().parse(purpose=purpose, system=system, user=user, schema=schema)


def test_withdrawal_during_a_turn_in_the_graph_discards_it_cdr_005(kb):  # noqa: F811
    model = HeldModel(
        {"translate": fake_model.translate, "tone_check": fake_model.tone_check, "trust": fake_model.trust}
    )
    model.app = create_app(model=model, settings=SETTINGS, kb=kb, voice=FakeVoice())
    with ConsentedClient(model.app) as client:
        sockets, (ctl, tv) = connect(client, "controller", "screen")
        try:
            submit(ctl, "physician", "en-CA", "Hello.")
            turn_id = drain_until(ctl, "turn.started")[-1]["payload"]["turnId"]
            # From the same controller connection: the turn in the graph must not hold the withdrawal back.
            withdraw_consent(ctl)
            ctl_events = drain_until_stage(ctl, "discarded")
            tv_events = drain_until_stage(tv, "discarded")
            assert "consent.changed" in types(ctl_events)
            for events in (ctl_events, tv_events):
                assert not {"turn.result", "turn.analysis"} & set(types(events))
            assert client.get(f"/api/speech/{turn_id}").status_code == 404
            command(ctl, "voice.started", speechId=turn_id, language="pa-IN")
            assert drain_until(ctl, "error")[-1]["payload"]["command"] == "voice.started"
            assert [e.payload["kind"] for e in client.app.state.hub.visit.chain.entries] == ["consent", "consent"]
            with client.websocket_connect("/ws/visit?role=screen") as late:
                state = late.receive_json()["payload"]
                assert state["turns"] == [] and state["currentTurn"] is None
        finally:
            close(sockets)


# ---------- the notice read aloud ----------


def test_consent_speak_reaches_controllers_once_on_first_set_and_on_read_aloud_cdr_005(client):
    sockets, (ctl, tv, phone) = connect(client, "controller", "screen", "review")
    try:
        set_languages(ctl, "pa-IN")
        speak = drain_until(ctl, "consent.speak")[-1]["payload"]
        assert speak == {"speechId": "consent-pa-IN-v1", "language": "pa-IN"}
        set_languages(ctl, "pa-IN")  # the same notice again: not read on its own a second time
        ctl_events, _ = marker(ctl)
        assert "consent.speak" not in types(ctl_events)
        command(phone, "consent.read_aloud")
        assert drain_until(ctl, "consent.speak")[-1]["payload"] == speak
        command(ctl, "consent.read_aloud")
        assert drain_until(ctl, "consent.speak")[-1]["payload"] == speak
        _, (tv_events, phone_events) = marker(ctl, tv, phone)
        assert "consent.speak" not in types(tv_events) + types(phone_events)
    finally:
        close(sockets)


def test_the_speak_gate_serves_the_current_notice_in_the_patients_language_only_cdr_005(kb):  # noqa: F811
    voice = FakeVoice()
    with make_client(kb, voice=voice, consent=False) as client:
        assert client.get("/api/speech/consent-pa-IN-v1?language=pa-IN").status_code == 200
        assert voice.said[-1] == (PA.lines[0].text, "pa-IN")
        for path in [
            "/api/speech/consent-pa-IN-v1?language=en-CA",
            "/api/speech/consent-pa-IN-v1",
            "/api/speech/consent-pa-IN-v0?language=pa-IN",
            "/api/speech/consent-fr-CA-v1?language=fr-CA",  # not this visit's notice
            "/api/speech/consent-unknown?language=pa-IN",
        ]:
            assert client.get(path).status_code == 404, path
        with client.websocket_connect("/ws/visit?role=controller") as ctl:
            ctl.receive_json()
            give_consent(ctl)
            drain_until(ctl, "consent.changed")
        # Served whether or not consent is given: it is not captured speech.
        assert client.get("/api/speech/consent-pa-IN-v1?language=pa-IN").status_code == 200


def test_voice_started_is_accepted_for_the_notice_cdr_005(client):
    sockets, (ctl, tv) = connect(client, "controller", "screen")
    try:
        command(ctl, "voice.started", speechId="consent-pa-IN-v1", language="pa-IN")
        speaking = drain_until(tv, "voice.speaking")[-1]["payload"]
        assert speaking == {"speaking": True, "speechId": "consent-pa-IN-v1", "language": "pa-IN"}
        command(ctl, "voice.started", speechId="consent-pa-IN-v1", language="en-CA")
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "voice.started"
    finally:
        close(sockets)


def test_nothing_private_reaches_screen_or_review_with_consent_cdr_005(kb):  # noqa: F811
    with make_client(kb) as client:
        sockets, (ctl, tv, phone) = connect(client, "controller", "screen", "review")
        try:
            submit(ctl, "patient", "pa-IN", "ਮੈਨੂੰ ਡਰ ਲੱਗਦਾ ਹੈ।")
            tv_events = drain_until(tv, "record.integrity")
            phone_events = drain_until(phone, "record.integrity")
            withdraw_consent(ctl)
            tv_events += drain_until(tv, "consent.changed")
            phone_events += drain_until(phone, "consent.changed")
            for events in (tv_events, phone_events):
                assert not contains_private(events)
                assert not {"consent.speak", "turn.analysis", "empathy.nudge", "error"} & set(types(events))
            for role in ("screen", "review"):
                with client.websocket_connect(f"/ws/visit?role={role}") as late:
                    state = late.receive_json()["payload"]
                    assert not contains_private(state)
                    assert not {"injection", "escalations", "nudges"} & state.keys()
        finally:
            close(sockets)
