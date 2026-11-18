"""Trust across the barrier on the visit channel (MDD-005, CDR-008, IDR-005, IDR-006): the patient's signals, trust
updates for the controller only, the reassurance rule and culture cues through the channel, the affect phrase in the
translation only, companion turns, the closing check, and a model that fails, all against the full turn graph with the scripted model (EDR-002)."""

import asyncio
import threading

from test_visit_channel import (
    SETTINGS,
    ConsentedClient,
    drain_until,
    drain_until_stage,
    give_consent,
    kb,  # noqa: F401  (fixture)
    make_client,
    set_names,
    submit,
    types,
    withdraw_consent,
)
from test_voice import FakeVoice
from visit_helpers import assert_public, close, command, connect, entries, kinds, marker, visit

import fake_model
from fake_model import CULTURE_CUE
from llm import ScriptedModel
from main import create_app
from trust import UNDERSTANDING_CUES

WORRIED_PA = "I am scared, ਮੈਨੂੰ ਬਹੁਤ ਡਰ ਲੱਗਦਾ ਹੈ।"
CALM_PA = "ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਡਾਕਟਰ ਜੀ।"
REASSURING_EN = "The tests were reassuring. You did not have a heart attack."
PLAIN_EN = "How long have you had the pain?"
SENSITIVE_EN = "How much alcohol do you drink in a week?"


def payloads(events, type_):
    return [e["payload"] for e in events if e["type"] == type_]


def signal(ws, kind):
    command(ws, "patient.signal", signal=kind)


def spoken(ctl, speaker, language, text) -> dict:
    """A turn through to its trust update on the controller; returns that update."""
    submit(ctl, speaker, language, text)
    return drain_until(ctl, "trust.update")[-1]["payload"]


def settle(*sockets):
    """Every role has the last settled turn's record.integrity, so later events are the next command's."""
    for ws in sockets:
        drain_until(ws, "record.integrity")


# ---------- patient signals (CDR-008) ----------


def test_signal_reaches_every_role_is_chained_and_relayed_to_the_physician_cdr_008(kb):  # noqa: F811
    with make_client(kb) as client:
        sockets, (ctl, tv, review) = connect(client, "controller", "screen", "review")
        try:
            set_names(ctl, patientName="Mr Singh")
            for ws in (ctl, tv, review):
                drain_until(ws, "visit.names")
            update = spoken(ctl, "physician", "en-CA", "Hello.")
            turn_id = update["turnId"]
            settle(tv, review)

            signal(review, "not_understood")
            review_events = drain_until(review, "interpreter.line")
            tv_events = drain_until(tv, "interpreter.line")
            ctl_events = drain_until(ctl, "trust.update")

            entry = payloads(review_events, "patient.signal")[0]
            assert entry["signal"] == "not_understood" and entry["afterTurnId"] == turn_id
            assert payloads(tv_events, "patient.signal") == [entry] == payloads(ctl_events, "patient.signal")
            # The interpreter relays it to the physician, in the physician's language only, naming the patient.
            line = payloads(ctl_events, "interpreter.line")[0]
            assert line["purpose"] == "signal_not_understood"
            assert line["lines"] == [
                {
                    "language": "en-CA",
                    "text": "Mr Singh is saying they did not understand that. Could you say it another way?",
                }
            ]
            assert payloads(tv_events, "interpreter.line") == [line] == payloads(review_events, "interpreter.line")
            # The chain holds a signal entry named by the signal id, and record.integrity followed the append.
            assert kinds(client)[-1] == "signal"
            chained = entries(client)[-1]
            assert chained["entryId"] == entry["signalId"] and chained["body"] == entry
            assert "record.integrity" in types(tv_events) and "record.integrity" in types(review_events)
            # The controller lists it with an understanding cue; screen and review hear nothing of that.
            trust = ctl_events[-1]["payload"]
            assert trust["signal"] == "not_understood" and trust["turnId"] == turn_id
            assert trust["cue"] == {"kind": "understanding", "text": UNDERSTANDING_CUES["not_understood"]}
            assert trust["speaker"] is None and trust["emotion"] is None and trust["reassuranceLanded"] is None
            assert "trust.update" not in types(tv_events) + types(review_events)
            assert_public(tv_events)
            assert_public(review_events)
            assert visit(client).signals == [visit(client).signals[0]] and len(visit(client).signals) == 1
        finally:
            close(sockets)
        with client.websocket_connect("/ws/visit?role=review") as late:
            state = late.receive_json()["payload"]
            assert state["signals"] == [entry] and "trust" not in state
        with client.websocket_connect("/ws/visit?role=controller") as late_ctl:
            state = late_ctl.receive_json()["payload"]
            assert state["signals"] == [entry]
            assert [t.get("signal") for t in state["trust"]] == [None, "not_understood"]


def test_slower_is_relayed_and_repeat_says_nothing_new_cdr_008(kb):  # noqa: F811
    with make_client(kb, signal_hold_s=0.0) as client:
        sockets, (ctl, tv, review) = connect(client, "controller", "screen", "review")
        try:
            spoken(ctl, "physician", "en-CA", "Hello.")
            settle(tv, review)
            signal(review, "slower")
            line = payloads(drain_until(ctl, "trust.update"), "interpreter.line")[0]
            assert line["purpose"] == "signal_slower"
            assert line["lines"][0]["text"] == "The patient is asking you to speak more slowly."
            drain_until(tv, "interpreter.line"), drain_until(review, "interpreter.line")

            signal(review, "repeat")
            ctl_events = drain_until(ctl, "trust.update")
            assert payloads(ctl_events, "patient.signal")[0]["signal"] == "repeat"
            assert "interpreter.line" not in types(ctl_events)  # the controller replays by id; nothing new is said
            assert ctl_events[-1]["payload"]["cue"]["text"] == UNDERSTANDING_CUES["repeat"]
            _, (tv_events, review_events) = marker(ctl, tv, review)
            assert "interpreter.line" not in types(tv_events) + types(review_events)
            assert [s.signal for s in visit(client).signals] == ["slower", "repeat"]
        finally:
            close(sockets)


def test_controller_copy_is_refused_and_screen_copy_is_dropped_cdr_008(kb):  # noqa: F811
    with make_client(kb) as client:
        sockets, (ctl, tv) = connect(client, "controller", "screen")
        try:
            spoken(ctl, "physician", "en-CA", "Hello.")
            settle(tv)
            signal(ctl, "not_understood")
            err = drain_until(ctl, "error")[-1]["payload"]
            assert err["command"] == "patient.signal"
            signal(tv, "not_understood")
            ctl_events, (tv_events,) = marker(ctl, tv)
            assert not {"patient.signal", "command.refused", "error"} & set(types(tv_events))
            assert "patient.signal" not in types(ctl_events)
            assert visit(client).signals == [] and "signal" not in kinds(client)
        finally:
            close(sockets)


def test_second_signal_within_two_seconds_is_busy_per_device_cdr_008(kb):  # noqa: F811
    with make_client(kb) as client:
        sockets, (ctl, review, tablet) = connect(client, "controller", "review", "review")
        try:
            spoken(ctl, "physician", "en-CA", "Hello.")
            settle(review, tablet)
            signal(review, "not_understood")
            drain_until(review, "interpreter.line"), drain_until(tablet, "interpreter.line")
            signal(review, "slower")
            refused = drain_until(review, "command.refused")[-1]["payload"]
            assert refused == {"command": "patient.signal", "reason": "busy"}
            # The hold is per device: another device may still signal.
            signal(tablet, "slower")
            assert payloads(drain_until(tablet, "interpreter.line"), "patient.signal")[0]["signal"] == "slower"
            assert [s.signal for s in visit(client).signals] == ["not_understood", "slower"]
        finally:
            close(sockets)


def test_repeat_before_any_spoken_translation_is_invalid_cdr_008(kb):  # noqa: F811
    with make_client(kb, signal_hold_s=0.0) as client:
        sockets, (ctl, review) = connect(client, "controller", "review")
        try:
            signal(review, "repeat")
            assert drain_until(review, "command.refused")[-1]["payload"]["reason"] == "invalid"
            # A patient turn is spoken in English, not in the patient's language: still nothing to repeat.
            spoken(ctl, "patient", "pa-IN", CALM_PA)
            settle(review)
            signal(review, "repeat")
            assert drain_until(review, "command.refused")[-1]["payload"]["reason"] == "invalid"
            update = spoken(ctl, "physician", "en-CA", "Hello.")
            settle(review)
            signal(review, "repeat")
            entry = drain_until(review, "patient.signal")[-1]["payload"]
            assert entry["signal"] == "repeat" and entry["afterTurnId"] == update["turnId"]
        finally:
            close(sockets)


def test_signals_are_refused_before_consent_and_while_paused_cdr_008(kb):  # noqa: F811
    with make_client(kb, consent=False, signal_hold_s=0.0) as client:
        sockets, (ctl, review) = connect(client, "controller", "review")
        try:
            signal(review, "not_understood")
            assert drain_until(review, "command.refused")[-1]["payload"]["reason"] == "invalid"
            give_consent(ctl)
            drain_until(review, "consent.changed")
            command(ctl, "visit.pause")
            drain_until(review, "visit.paused")
            signal(review, "not_understood")
            assert drain_until(review, "command.refused")[-1]["payload"]["reason"] == "invalid"
            command(ctl, "visit.resume")
            drain_until(review, "visit.resumed")
            signal(review, "not_understood")
            entry = drain_until(review, "patient.signal")[-1]["payload"]
            assert entry["signal"] == "not_understood" and entry["afterTurnId"] is None
            assert visit(client).signals[0].after_turn_id is None
        finally:
            close(sockets)


# ---------- trust updates (CDR-008) ----------


def test_trust_update_per_spoken_turn_reaches_the_controller_only_cdr_008(kb):  # noqa: F811
    with make_client(kb) as client:
        sockets, (ctl, tv, review) = connect(client, "controller", "screen", "review")
        try:
            update = spoken(ctl, "physician", "en-CA", PLAIN_EN)
            assert update["speaker"] == "physician" and update["manner"] == "plain"
            assert update["emotion"] is None and update["reassuranceLanded"] is None
            assert update["signal"] is None and update["cue"] is None
            settle(tv, review)
            _, (tv_events, review_events) = marker(ctl, tv, review)
            for events in (tv_events, review_events):
                assert "trust.update" not in types(events)
                assert_public(events)
        finally:
            close(sockets)
        for role in ("screen", "review"):
            with client.websocket_connect(f"/ws/visit?role={role}") as late:
                state = late.receive_json()["payload"]
                assert "trust" not in state and state["signals"] == []
        with client.websocket_connect("/ws/visit?role=controller") as late_ctl:
            assert late_ctl.receive_json()["payload"]["trust"] == [update]


def test_reassurance_landed_true_false_and_null_through_the_channel_cdr_008(kb):  # noqa: F811
    with make_client(kb) as client:
        sockets, (ctl,) = connect(client, "controller")
        try:
            # A calm turn with no earlier worry: no mark.
            physician = spoken(ctl, "physician", "en-CA", REASSURING_EN)
            assert physician["manner"] == "reassuring"
            assert spoken(ctl, "patient", "pa-IN", CALM_PA)["reassuranceLanded"] is None
            # Worry: the emotion is shown, the nudge is sent, no mark yet.
            submit(ctl, "patient", "pa-IN", WORRIED_PA)
            events = drain_until(ctl, "trust.update")
            worried = events[-1]["payload"]
            assert worried["emotion"] == "worried" and worried["reassuranceLanded"] is None
            assert payloads(events, "empathy.nudge")[0]["turnId"] == worried["turnId"]
            assert worried["cue"]["kind"] == "reassurance"
            # Reassurance, then calm: landed. Reassurance, then worry again: not yet.
            spoken(ctl, "physician", "en-CA", REASSURING_EN)
            landed = spoken(ctl, "patient", "pa-IN", CALM_PA)
            assert landed["reassuranceLanded"] is True and landed["emotion"] == "calm"
            # Landed resets the pair: a later calm turn has no mark, and a new worry has none until reassured.
            assert spoken(ctl, "patient", "pa-IN", CALM_PA)["reassuranceLanded"] is None
            assert spoken(ctl, "patient", "pa-IN", WORRIED_PA)["reassuranceLanded"] is None
            # A new reassurance, then still worried: not yet.
            spoken(ctl, "physician", "en-CA", REASSURING_EN)
            assert spoken(ctl, "patient", "pa-IN", WORRIED_PA)["reassuranceLanded"] is False
        finally:
            close(sockets)
        with client.websocket_connect("/ws/visit?role=controller") as late:
            state = late.receive_json()["payload"]
            assert [t["reassuranceLanded"] for t in state["trust"]] == [
                None,
                None,
                None,
                None,
                True,
                None,
                None,
                None,
                False,
            ]
            assert [t["emotion"] for t in state["trust"] if t["speaker"] == "patient"] == [
                "calm",
                "worried",
                "calm",
                "calm",
                "worried",
                "worried",
            ]


def test_culture_cue_on_a_sensitive_topic_and_none_on_an_everyday_one_cdr_008(kb):  # noqa: F811
    with make_client(kb) as client:
        sockets, (ctl,) = connect(client, "controller")
        try:
            sensitive = spoken(ctl, "physician", "en-CA", SENSITIVE_EN)
            assert sensitive["cue"] == {"kind": "culture", "text": CULTURE_CUE}
            assert spoken(ctl, "physician", "en-CA", PLAIN_EN)["cue"] is None
            # Nothing of the trust layer is chained: the record holds consent and the two turns only.
            assert kinds(client) == ["consent", "turn", "turn"]
            assert not any("cue" in str(e) or "reassurance" in str(e) for e in entries(client))
        finally:
            close(sockets)


def test_a_confirmed_readback_gets_its_trust_update_cdr_008(kb):  # noqa: F811
    with make_client(kb) as client:
        sockets, (ctl,) = connect(client, "controller")
        try:
            submit(
                ctl, "physician", "en-CA", "Use the nitroglycerin spray: 0.4 milligrams, one spray under your tongue."
            )
            turn_id = drain_until_stage(ctl, "awaiting_readback")[-1]["payload"]["turnId"]
            command(ctl, "turn.readback_confirm", turnId=turn_id)
            update = drain_until(ctl, "trust.update")[-1]["payload"]
            assert update["turnId"] == turn_id and update["speaker"] == "physician"
        finally:
            close(sockets)


def test_a_failing_advisor_still_yields_a_trust_update_without_a_cue_cdr_008(kb):  # noqa: F811
    def broken(user):
        raise RuntimeError("advisor down")

    with make_client(kb, handlers={"trust": broken}) as client:
        sockets, (ctl,) = connect(client, "controller")
        try:
            assert spoken(ctl, "physician", "en-CA", SENSITIVE_EN)["cue"] is None
            submit(ctl, "patient", "pa-IN", WORRIED_PA)
            events = drain_until(ctl, "trust.update")
            assert "empathy.nudge" not in types(events) and events[-1]["payload"]["emotion"] == "worried"
        finally:
            close(sockets)


def held_advisor():
    """A trust handler whose first call waits until the returned gate is set (a slow model), then answers as the
    faithful fake; every later call answers at once. Also returns the calls it has seen."""
    gate, seen = threading.Event(), []

    async def handler(user):
        seen.append(user)
        if len(seen) == 1:
            while not gate.is_set():
                await asyncio.sleep(0.01)
        return fake_model.trust(user)

    return handler, gate, seen


def test_a_slow_turn_update_is_listed_before_later_turns_and_the_signal_after_it_cdr_008(kb):  # noqa: F811
    handler, gate, _ = held_advisor()
    with make_client(kb, handlers={"trust": handler}) as client:
        sockets, (ctl, review) = connect(client, "controller", "review")
        try:
            # Turn 1's advisor is slow; turn 2's update and a signal after turn 2 arrive before turn 1's.
            submit(ctl, "physician", "en-CA", PLAIN_EN)
            first = drain_until(ctl, "turn.result")[-1]["payload"]["turnId"]
            second = spoken(ctl, "physician", "en-CA", SENSITIVE_EN)["turnId"]
            signal(review, "not_understood")
            live = drain_until(ctl, "trust.update")[-1]["payload"]
            assert live["signal"] == "not_understood" and live["turnId"] == second
            gate.set()
            late = drain_until(ctl, "trust.update")[-1]["payload"]
            assert late["turnId"] == first and late["signal"] is None
        finally:
            close(sockets)
        # The visit keeps the timeline in spoken order, so a fresh controller lists turn 1 first.
        with client.websocket_connect("/ws/visit?role=controller") as fresh:
            trust = fresh.receive_json()["payload"]["trust"]
            assert [(t["turnId"], t["signal"]) for t in trust] == [
                (first, None),
                (second, None),
                (second, "not_understood"),
            ]


def test_a_signal_after_a_slow_turn_is_listed_after_that_turns_update_cdr_008(kb):  # noqa: F811
    handler, gate, _ = held_advisor()
    with make_client(kb, handlers={"trust": handler}) as client:
        sockets, (ctl, review) = connect(client, "controller", "review")
        try:
            submit(ctl, "physician", "en-CA", PLAIN_EN)
            turn_id = drain_until(ctl, "turn.result")[-1]["payload"]["turnId"]
            drain_until(review, "turn.result")
            signal(review, "slower")
            assert drain_until(ctl, "trust.update")[-1]["payload"]["signal"] == "slower"
            gate.set()
            assert drain_until(ctl, "trust.update")[-1]["payload"]["turnId"] == turn_id
        finally:
            close(sockets)
        with client.websocket_connect("/ws/visit?role=controller") as fresh:
            trust = fresh.receive_json()["payload"]["trust"]
            assert [(t["turnId"], t["signal"]) for t in trust] == [(turn_id, None), (turn_id, "slower")]


def test_consent_withdrawn_while_the_advisor_runs_drops_the_trust_update_cdr_008(kb):  # noqa: F811
    handler, gate, seen = held_advisor()
    with make_client(kb, handlers={"trust": handler}) as client:
        sockets, (ctl,) = connect(client, "controller")
        try:
            submit(ctl, "patient", "pa-IN", WORRIED_PA)
            drain_until(ctl, "turn.result")
            withdraw_consent(ctl)
            drain_until(ctl, "consent.changed")
            gate.set()
            events, _ = marker(ctl)
            # Dropped: no nudge and no trust update, and no further model call for this turn.
            assert "trust.update" not in types(events) and "empathy.nudge" not in types(events)
            assert len(seen) == 1
            assert visit(client).trust == [] and visit(client).nudges == []
        finally:
            close(sockets)


# ---------- manner on the wire (IDR-005, CDR-008) ----------


def test_physician_caption_carries_manner_and_patient_caption_never_does_cdr_008(kb):  # noqa: F811
    with make_client(kb) as client:
        sockets, (ctl, tv) = connect(client, "controller", "screen")
        try:
            spoken(ctl, "physician", "en-CA", REASSURING_EN)
            caption = drain_until(tv, "turn.result")[-1]["payload"]
            assert caption["speaker"] == "physician" and caption["manner"] == "reassuring"
            spoken(ctl, "patient", "pa-IN", WORRIED_PA)
            caption = drain_until(tv, "turn.result")[-1]["payload"]
            assert caption["speaker"] == "patient" and caption["manner"] is None
            # The chain carries the same: the physician's manner, and nothing for the patient.
            turns = [e["body"] for e in entries(client) if e["kind"] == "turn"]
            assert [t["manner"] for t in turns] == ["reassuring", None]
        finally:
            close(sockets)


# ---------- affect in words (IDR-006, MDD-006) ----------

WORRIED_PHRASE = "sounding worried"


def labels(obj) -> list[str]:
    """Every manner or emotion key with a value, anywhere in a payload."""
    if isinstance(obj, dict):
        own = [k for k in ("manner", "emotion") if obj.get(k) is not None]
        return own + [label for v in obj.values() for label in labels(v)]
    if isinstance(obj, list):
        return [label for v in obj for label in labels(v)]
    return []


def phrase_places(obj, path="") -> list[str]:
    """Where the affect phrase appears in a payload, by key path."""
    if isinstance(obj, dict):
        return [p for k, v in obj.items() for p in phrase_places(v, f"{path}.{k}")]
    if isinstance(obj, list):
        return [p for v in obj for p in phrase_places(v, path)]
    return [path] if isinstance(obj, str) and WORRIED_PHRASE in obj else []


def test_worried_patient_label_reaches_the_controller_only_and_the_phrase_only_the_translation_idr_006(kb):  # noqa: F811
    with make_client(kb) as client:
        sockets, (ctl, tv, review) = connect(client, "controller", "screen", "review")
        try:
            submit(ctl, "patient", "pa-IN", WORRIED_PA)
            ctl_events = drain_until(ctl, "trust.update")
            tv_events, review_events = drain_until(tv, "record.integrity"), drain_until(review, "record.integrity")
        finally:
            close(sockets)
    # The controller still gets the emotion and manner as a label, in the analysis and the trust update.
    analysis = payloads(ctl_events, "turn.analysis")[0]
    assert analysis["emotion"] == "worried" and analysis["manner"] == "plain"
    update = ctl_events[-1]["payload"]
    assert update["speaker"] == "patient" and update["emotion"] == "worried" and update["manner"] == "plain"
    # The shared screen and the patient's device get no manner or emotion label, and the phrase only in translation.
    for events in (tv_events, review_events):
        assert_public(events)
        assert all(labels(e["payload"]) == [] for e in events)
        caption = payloads(events, "turn.result")[0]
        assert caption["manner"] is None and caption["translation"].count(WORRIED_PHRASE) == 1
        assert [p for e in events for p in phrase_places(e["payload"])] == [".translation"]


def test_speak_gate_speaks_the_worried_patient_relay_with_its_phrase_and_refuses_non_final_turns_idr_006(kb):  # noqa: F811
    voice = FakeVoice()
    model = ScriptedModel(
        {"translate": fake_model.translate, "tone_check": fake_model.tone_check, "trust": fake_model.trust}
    )
    with (
        ConsentedClient(create_app(model=model, settings=SETTINGS, kb=kb, voice=voice)) as client,
        client.websocket_connect("/ws/visit?role=controller") as ctl,
    ):
        ctl.receive_json()
        submit(ctl, "patient", "pa-IN", WORRIED_PA)
        caption = drain_until(ctl, "turn.result")[-1]["payload"]
        assert caption["status"] == "final"
        assert client.get(f"/api/speech/{caption['turnId']}").status_code == 200
        assert voice.said == [(caption["translation"], "en-CA")]
        assert caption["translation"].startswith(f"[en-CA] The patient says, {WORRIED_PHRASE}, ")
        # Unclear, escalated, and blocked worried turns are refused as before, phrase or not.
        for marker_ in (fake_model.UNCLEAR_MARKER, fake_model.TONE_MARKER, fake_model.MISMATCH_MARKER):
            submit(ctl, "patient", "pa-IN", f"{WORRIED_PA} 2 {marker_}")
            refused = drain_until(ctl, "turn.result")[-1]["payload"]
            assert refused["status"] in {"unclear", "escalated", "blocked"}
            assert client.get(f"/api/speech/{refused['turnId']}").status_code == 404
    assert len(voice.said) == 1


def test_patient_turn_in_the_physicians_language_is_relayed_to_the_patient_without_a_phrase_idr_006(kb):  # noqa: F811
    """Review fix 4: the server tells the turn graph the relay is for the patient, so no phrase is spoken to them."""
    model = ScriptedModel(
        {"translate": fake_model.translate, "tone_check": fake_model.tone_check, "trust": fake_model.trust}
    )
    with (
        ConsentedClient(create_app(model=model, settings=SETTINGS, kb=kb)) as client,
        client.websocket_connect("/ws/visit?role=controller") as ctl,
    ):
        ctl.receive_json()
        submit(ctl, "patient", "en-CA", "I am scared of the needle.")
        caption = drain_until(ctl, "turn.result")[-1]["payload"]
        assert caption["status"] == "final" and caption["targetLanguage"] == "pa-IN"
        assert WORRIED_PHRASE not in caption["translation"] and " says, " not in caption["translation"]
        user = next(u for purpose, u in model.calls if purpose == "translate")
        assert fake_model.field(user, "listener") == "patient"
        # The same speaker in their own language is relayed to the physician, with the phrase.
        submit(ctl, "patient", "pa-IN", WORRIED_PA)
        caption = drain_until(ctl, "turn.result")[-1]["payload"]
        assert caption["targetLanguage"] == "en-CA" and WORRIED_PHRASE in caption["translation"]


# ---------- companion turns (CDR-008) ----------


def test_companion_turn_is_accepted_in_the_patients_language_and_labelled_everywhere_cdr_008(kb):  # noqa: F811
    model = ScriptedModel(
        {"translate": fake_model.translate, "tone_check": fake_model.tone_check, "trust": fake_model.trust}
    )
    with ConsentedClient(create_app(model=model, settings=SETTINGS, kb=kb)) as client:
        sockets, (ctl, tv, review) = connect(client, "controller", "screen", "review")
        try:
            set_names(ctl, physicianName="Dr. Thomas")
            for ws in (ctl, tv, review):
                drain_until(ws, "visit.names")
            submit(ctl, "companion", "pa-IN", WORRIED_PA)
            ctl_events = drain_until(ctl, "trust.update")
            assert payloads(ctl_events, "turn.started")[0]["speaker"] == "companion"
            caption = payloads(ctl_events, "turn.result")[0]
            assert caption["speaker"] == "companion" and caption["manner"] is None
            assert caption["targetLanguage"] == "en-CA"
            assert payloads(drain_until(tv, "turn.result"), "turn.result")[0]["speaker"] == "companion"
            assert payloads(drain_until(review, "turn.result"), "turn.result")[0]["speaker"] == "companion"
            # The emotion reaches the trust view; no nudge and no landed mark come from a companion.
            update = ctl_events[-1]["payload"]
            assert update["speaker"] == "companion" and update["emotion"] == "worried"
            assert update["reassuranceLanded"] is None and update["cue"] is None
            assert "empathy.nudge" not in types(ctl_events) and visit(client).nudges == []
            # Chained as the companion's, and relayed with the companion frame.
            turn = entries(client)[-1]
            assert turn["kind"] == "turn" and turn["body"]["speaker"] == "companion"
            user = next(u for purpose, u in model.calls if purpose == "translate")
            assert fake_model.field(user, "speaker") == "companion"
            assert fake_model.field(user, "speaker_name") == "the patient's companion"
            assert fake_model.field(user, "listener_name") == "Dr. Thomas"
        finally:
            close(sockets)
        with client.websocket_connect("/ws/visit?role=controller") as late:
            state = late.receive_json()["payload"]
            assert state["turns"][0]["speaker"] == "companion"
        with client.websocket_connect("/ws/visit?role=screen") as late:
            assert late.receive_json()["payload"]["turns"][0]["speaker"] == "companion"


def test_companion_turn_in_the_physicians_language_is_refused_cdr_008(kb):  # noqa: F811
    with make_client(kb) as client:
        sockets, (ctl, tv) = connect(client, "controller", "screen")
        try:
            submit(ctl, "companion", "en-CA", "She has been dizzy since Monday.")
            err = drain_until(ctl, "error")[-1]["payload"]
            assert err["command"] == "turn.submit" and err["message"] == "A companion speaks the patient's language"
            _, (tv_events,) = marker(ctl, tv)
            assert "turn.started" not in types(tv_events)
            assert visit(client).turns == {}
        finally:
            close(sockets)


# ---------- the closing check (CDR-008) ----------


def ask(ctl):
    command(ctl, "visit.ask_if_clear")


def test_ask_if_clear_says_one_line_in_two_languages_spoken_in_the_patients_only_cdr_008(kb):  # noqa: F811
    voice = FakeVoice()
    with make_client(kb, voice=voice) as client:
        sockets, (ctl, tv, review) = connect(client, "controller", "screen", "review")
        try:
            set_names(ctl, patientName="Harpreet")
            for ws in (ctl, tv, review):
                drain_until(ws, "visit.names")
            ask(ctl)
            line = drain_until(ctl, "interpreter.line")[-1]["payload"]
            assert line["purpose"] == "ask_if_clear"
            assert [part["language"] for part in line["lines"]] == ["pa-IN", "en-CA"]
            assert all("Harpreet" in part["text"] for part in line["lines"])
            assert line["lines"][1]["text"].endswith("that you would like explained again?")
            assert drain_until(tv, "interpreter.line")[-1]["payload"] == line
            assert drain_until(review, "interpreter.line")[-1]["payload"] == line
            # The speak gate serves the patient's language only; the physician's copy is shown, never spoken.
            assert client.get(f"/api/speech/{line['lineId']}?language=pa-IN").status_code == 200
            assert client.get(f"/api/speech/{line['lineId']}?language=en-CA").status_code == 404
            assert voice.said == [(line["lines"][0]["text"], "pa-IN")]
            command(ctl, "voice.started", speechId=line["lineId"], language="en-CA")
            assert drain_until(ctl, "error")[-1]["payload"]["command"] == "voice.started"
            command(ctl, "voice.started", speechId=line["lineId"], language="pa-IN")
            assert drain_until(tv, "voice.speaking")[-1]["payload"]["language"] == "pa-IN"
            # Nothing is chained for it: the interpreter's own lines are not record entries (CDR-006).
            assert kinds(client) == ["consent"]
        finally:
            close(sockets)


def test_ask_if_clear_is_refused_before_consent_while_paused_and_during_a_readback_cdr_008(kb):  # noqa: F811
    with make_client(kb, consent=False) as client:
        sockets, (ctl, tv) = connect(client, "controller", "screen")
        try:
            ask(ctl)
            assert drain_until(ctl, "error")[-1]["payload"]["command"] == "visit.ask_if_clear"
            give_consent(ctl)
            drain_until(ctl, "consent.changed"), drain_until(tv, "consent.changed")
            command(ctl, "visit.pause")
            drain_until(ctl, "visit.paused")
            ask(ctl)
            assert "Paused" in drain_until(ctl, "error")[-1]["payload"]["message"]
            command(ctl, "visit.resume")
            drain_until(ctl, "visit.resumed")
            submit(
                ctl, "physician", "en-CA", "Use the nitroglycerin spray: 0.4 milligrams, one spray under your tongue."
            )
            turn_id = drain_until_stage(ctl, "awaiting_readback")[-1]["payload"]["turnId"]
            ask(ctl)
            assert "dose" in drain_until(ctl, "error")[-1]["payload"]["message"]
            command(ctl, "turn.readback_reject", turnId=turn_id)
            drain_until_stage(ctl, "discarded")
            ask(ctl)
            assert drain_until(ctl, "interpreter.line")[-1]["payload"]["purpose"] == "ask_if_clear"
            drain_until(tv, "interpreter.line")
            # A screen or review copy is dropped: the command is the controller's.
            ask(tv)
            _, (tv_events,) = marker(ctl, tv)
            assert "interpreter.line" not in types(tv_events)
        finally:
            close(sockets)


# ---------- a model that fails (ADR-004, ADR-006, CDR-001) ----------


def test_a_failing_model_ends_the_turn_as_failed_with_nothing_spoken_or_chained_cdr_001(kb):  # noqa: F811
    def hung(user):
        raise TimeoutError("the model did not answer in 25 seconds")

    voice = FakeVoice()
    with make_client(kb, translate=hung, voice=voice) as client:
        sockets, (ctl, tv) = connect(client, "controller", "screen")
        try:
            submit(ctl, "physician", "en-CA", "Hello.")
            ctl_events = drain_until(ctl, "error")
            turn_id = payloads(ctl_events, "turn.started")[0]["turnId"]
            assert [e["payload"]["stage"] for e in ctl_events if e["type"] == "turn.status"][-1] == "failed"
            assert ctl_events[-1]["payload"]["command"] == "turn.submit"
            tv_events = drain_until_stage(tv, "failed")
            assert "turn.result" not in types(ctl_events) + types(tv_events)
            assert client.get(f"/api/speech/{turn_id}").status_code == 404 and voice.said == []
            assert kinds(client) == ["consent"]
            # The visit goes on: the next turn is relayed as usual.
            _, (tv_events,) = marker(ctl, tv)
            assert "trust.update" not in types(ctl_events)
        finally:
            close(sockets)
