"""Visit channel tests: role routing, snapshots, languages, read-back, blocking, escalation,
empathy nudges, names, the introduction, and voice playback, run against the full turn graph with a scripted
model (CDR-001, CDR-002, CDR-003, CDR-004)."""

import pytest
from fastapi.testclient import TestClient

import fake_model
from config import Settings
from graph.turn_graph import Draft, ToneCheck
from kb.embeddings import HashingEmbedder
from kb.store import KnowledgeBase
from llm import ScriptedModel
from main import create_app

SETTINGS = Settings(translator="fake", azure_speech_key=None, azure_speech_region=None)
PRIVATE_KEYS = {"emotion", "certainty", "backTranslation", "nudges", "toneTags", "confidence"}
DOSE = "Use the nitroglycerin spray: 0.4 milligrams, one spray under your tongue."


@pytest.fixture(scope="module")
def kb():
    return KnowledgeBase(HashingEmbedder())


def give_consent(ws, language="pa-IN"):
    """consent.give for the visit's current notice, from whichever role `ws` is (CDR-005)."""
    ws.send_json({"type": "consent.give", "payload": {"noticeVersion": "1", "language": language}})


def withdraw_consent(ws, reason=None):
    ws.send_json({"type": "consent.withdraw", "payload": {} if reason is None else {"reason": reason}})


class ConsentedClient(TestClient):
    """A test client whose visit starts with consent given by a controller, through the real command path.

    Consent gates every speech-capturing command (CDR-005), so tests about anything else start here; the
    consent tests themselves pass `consent=False`.
    """

    def __init__(self, app, consent: bool = True, language: str = "pa-IN") -> None:
        super().__init__(app)
        self._consent = consent
        self._language = language

    def __enter__(self):
        client = super().__enter__()
        if self._consent:
            with client.websocket_connect("/ws/visit?role=controller") as ctl:
                ctl.receive_json()
                if self._language != "pa-IN":
                    set_languages(ctl, self._language)
                    drain_until(ctl, "visit.state")
                give_consent(ctl, self._language)
                drain_until(ctl, "consent.changed")
        return client


def set_languages(ws, patient_language):
    ws.send_json(
        {"type": "visit.set_languages", "payload": {"patientLanguage": patient_language, "physicianLanguage": "en-CA"}}
    )


def make_client(kb, translate=None, tone_check=None, consent=True, language="pa-IN", settings=None, **app_options):
    model = ScriptedModel(
        {
            "translate": translate or fake_model.translate,
            "tone_check": tone_check or fake_model.tone_check,
            "empathy": fake_model.empathy,
            "name_extract": fake_model.name_extract,
        }
    )
    app = create_app(model=model, settings=settings or SETTINGS, kb=kb, **app_options)
    return ConsentedClient(app, consent=consent, language=language)


@pytest.fixture
def client(kb):
    # One event loop for every connection, as under uvicorn; separate portals never wake each other.
    with make_client(kb) as c:
        yield c


def submit(ws, speaker, language, text, confidence=0.95):
    ws.send_json(
        {
            "type": "turn.submit",
            "payload": {"speaker": speaker, "language": language, "text": text, "recognitionConfidence": confidence},
        }
    )


def drain_until(ws, event_type):
    seen = []
    while True:
        event = ws.receive_json()
        seen.append(event)
        if event["type"] == event_type:
            return seen


def drain_until_stage(ws, stage):
    seen = []
    while True:
        event = ws.receive_json()
        seen.append(event)
        if event["type"] == "turn.status" and event["payload"]["stage"] == stage:
            return seen


def contains_private(obj) -> bool:
    if isinstance(obj, dict):
        return bool(PRIVATE_KEYS & obj.keys()) or any(contains_private(v) for v in obj.values())
    if isinstance(obj, list):
        return any(contains_private(v) for v in obj)
    return False


def types(events):
    return [e["type"] for e in events]


# ---------- routing and snapshots ----------


def test_connect_sends_role_filtered_state(client):
    with (
        client.websocket_connect("/ws/visit?role=controller") as ctl,
        client.websocket_connect("/ws/visit?role=screen") as tv,
    ):
        ctl_state, tv_state = ctl.receive_json(), tv.receive_json()
        assert ctl_state["type"] == tv_state["type"] == "visit.state"
        assert "nudges" in ctl_state["payload"] and "nudges" not in tv_state["payload"]
        assert tv_state["payload"]["patientLanguage"] == "pa-IN"


def test_patient_turn_reaches_screen_without_private_fields(client):
    with (
        client.websocket_connect("/ws/visit?role=controller") as ctl,
        client.websocket_connect("/ws/visit?role=screen") as tv,
    ):
        ctl.receive_json(), tv.receive_json()
        submit(ctl, "patient", "pa-IN", "ਸਤ ਸ੍ਰੀ ਅਕਾਲ")
        ctl_events = drain_until(ctl, "turn.result")
        tv_events = drain_until(tv, "turn.result")

        assert "turn.analysis" in types(ctl_events)
        assert "turn.analysis" not in types(tv_events)
        stages = [e["payload"]["stage"] for e in tv_events if e["type"] == "turn.status"]
        assert {"checking_glossary", "translating", "verifying"} <= set(stages)
        caption = tv_events[-1]["payload"]
        assert caption["translation"] == "[en-CA] ਸਤ ਸ੍ਰੀ ਅਕਾਲ" and caption["toneLabel"] == "respectful"
        assert not any(contains_private(e) for e in tv_events)
        assert [e["seq"] for e in tv_events] == list(range(2, 2 + len(tv_events)))  # no gaps on screens


def test_screen_connecting_later_gets_settled_turns_only(client):
    with client.websocket_connect("/ws/visit?role=controller") as ctl:
        ctl.receive_json()
        submit(ctl, "physician", "en-CA", "Hello.")
        drain_until(ctl, "turn.result")
    with client.websocket_connect("/ws/visit?role=screen") as tv:
        state = tv.receive_json()
        assert state["payload"]["turns"][0]["translation"] == "[pa-IN] Hello."
        assert not contains_private(state)


def test_set_languages_before_first_turn_then_rejected(kb):
    with make_client(kb, consent=False) as client, client.websocket_connect("/ws/visit?role=controller") as ctl:
        ctl.receive_json()
        set_languages(ctl, "fr-CA")
        assert ctl.receive_json()["payload"]["patientLanguage"] == "fr-CA"
        give_consent(ctl, "fr-CA")
        drain_until(ctl, "consent.changed")
        submit(ctl, "patient", "fr-CA", "Bonjour")
        drain_until(ctl, "turn.result")
        # Withdrawn consent unlocks the languages (CDR-005), but the visit has a turn, so they stay fixed.
        withdraw_consent(ctl)
        drain_until(ctl, "consent.changed")
        set_languages(ctl, "pa-IN")
        err = drain_until(ctl, "error")[-1]
        assert err["payload"]["command"] == "visit.set_languages" and "turn" in err["payload"]["message"]


def test_screen_cannot_send_controller_commands(client):
    with (
        client.websocket_connect("/ws/visit?role=screen") as tv,
        client.websocket_connect("/ws/visit?role=controller") as ctl,
    ):
        tv.receive_json(), ctl.receive_json()
        submit(tv, "patient", "pa-IN", "x")
        set_names(ctl, patientName="Marker")
        assert ctl.receive_json()["type"] == "visit.names"  # no turn started, so the screen's submit was ignored
    assert client.app.state.hub.visit.turns == {}


def test_speech_token_unconfigured_returns_503(client):
    assert client.get("/api/speech-token").status_code == 503


# ---------- read-back (task 2.6) ----------


def test_dose_waits_for_physician_confirmation_then_is_spoken(client):
    with (
        client.websocket_connect("/ws/visit?role=controller") as ctl,
        client.websocket_connect("/ws/visit?role=screen") as tv,
    ):
        ctl.receive_json(), tv.receive_json()
        submit(ctl, "physician", "en-CA", DOSE)
        ctl_events = drain_until_stage(ctl, "awaiting_readback")
        tv_events = drain_until_stage(tv, "awaiting_readback")
        assert "turn.readback_required" in types(ctl_events)
        assert "turn.result" not in types(ctl_events) + types(tv_events)  # nothing spoken or shown yet
        turn_id = ctl_events[-1]["payload"]["turnId"]

        # A screen connecting during read-back sees no translation and no private data.
        with client.websocket_connect("/ws/visit?role=screen") as late:
            state = late.receive_json()
            assert state["payload"]["currentTurn"]["stage"] == "awaiting_readback"
            assert state["payload"]["turns"] == [] and not contains_private(state)

        submit(ctl, "physician", "en-CA", "Next line.")
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "turn.submit"

        ctl.send_json({"type": "turn.readback_confirm", "payload": {"turnId": turn_id}})
        caption = drain_until(tv, "turn.result")[-1]["payload"]
        assert caption["status"] == "final" and caption["readbackConfirmed"] is True
        assert caption["criticalValues"] and "0.4" in caption["translation"]


def test_rejected_readback_is_discarded_unspoken(client):
    with (
        client.websocket_connect("/ws/visit?role=controller") as ctl,
        client.websocket_connect("/ws/visit?role=screen") as tv,
    ):
        ctl.receive_json(), tv.receive_json()
        submit(ctl, "physician", "en-CA", DOSE)
        turn_id = drain_until_stage(ctl, "awaiting_readback")[-1]["payload"]["turnId"]
        drain_until_stage(tv, "awaiting_readback")
        ctl.send_json({"type": "turn.readback_reject", "payload": {"turnId": turn_id}})
        assert drain_until_stage(tv, "discarded")
        submit(ctl, "physician", "en-CA", "Hello.")  # free to continue
        assert drain_until(tv, "turn.result")[-1]["payload"]["sourceText"] == "Hello."


# ---------- blocked and escalated ----------


def test_blocked_dose_never_reaches_screen(kb):
    def wrong(user):
        d = fake_model.translate(user)
        return Draft(**{**d.model_dump(), "translation": d.translation.replace("0.4", "4")})

    with (
        make_client(kb, translate=wrong) as client,
        client.websocket_connect("/ws/visit?role=controller") as ctl,
        client.websocket_connect("/ws/visit?role=screen") as tv,
    ):
        ctl.receive_json(), tv.receive_json()
        submit(ctl, "physician", "en-CA", DOSE)
        analysis = next(e for e in drain_until(ctl, "turn.result") if e["type"] == "turn.analysis")
        assert analysis["payload"]["status"] == "blocked"
        tv_events = drain_until(tv, "turn.result")
        caption = tv_events[-1]["payload"]
        assert caption["status"] == "blocked" and caption["translation"] is None and caption["criticalValues"] == []
        assert not any("[pa-IN]" in str(e) for e in tv_events)  # no draft translation, wrong or otherwise
        assert "interpreter.escalation" not in types(tv_events)


def test_tone_failure_escalates_with_reason(kb):
    def failing(user):
        return ToneCheck(meaning_preserved=True, certainty_preserved=False, warmth_preserved=True, issue="x")

    with (
        make_client(kb, tone_check=failing) as client,
        client.websocket_connect("/ws/visit?role=controller") as ctl,
        client.websocket_connect("/ws/visit?role=screen") as tv,
    ):
        ctl.receive_json(), tv.receive_json()
        submit(ctl, "physician", "en-CA", "This is very unlikely to be serious.")
        drain_until(tv, "turn.result")
        escalation = drain_until(tv, "interpreter.escalation")[-1]["payload"]
        assert escalation["reason"] == "tone_failure"


# ---------- empathy nudges (task 2.5) ----------


def test_empathy_nudge_reaches_controller_only(client):
    with (
        client.websocket_connect("/ws/visit?role=controller") as ctl,
        client.websocket_connect("/ws/visit?role=screen") as tv,
    ):
        ctl.receive_json(), tv.receive_json()
        submit(ctl, "patient", "pa-IN", "I am scared, ਮੈਨੂੰ ਬਹੁਤ ਡਰ ਲੱਗਦਾ ਹੈ।")
        nudge = drain_until(ctl, "empathy.nudge")[-1]["payload"]
        assert nudge["emotion"] == "worried" and nudge["phrase"] and nudge["phraseLanguage"] == "en-CA"
        tv_events = drain_until(tv, "turn.result")
        assert "empathy.nudge" not in types(tv_events)
    with (
        client.websocket_connect("/ws/visit?role=screen") as late,
        client.websocket_connect("/ws/visit?role=controller") as ctl2,
    ):
        assert not contains_private(late.receive_json())
        assert ctl2.receive_json()["payload"]["nudges"][0]["emotion"] == "worried"


# ---------- names (CDR-003) ----------


def set_names(ws, **names):
    ws.send_json({"type": "visit.set_names", "payload": names})


def test_set_names_reaches_every_screen_and_snapshot(client):
    with (
        client.websocket_connect("/ws/visit?role=controller") as ctl,
        client.websocket_connect("/ws/visit?role=screen") as tv,
    ):
        assert ctl.receive_json()["payload"]["introduction"] == "pending"
        tv.receive_json()
        set_names(ctl, physicianName="  Dr. Thomas ", patientName="Harpreet")
        for ws in (ctl, tv):
            event = ws.receive_json()
            assert event["type"] == "visit.names"
            assert event["payload"] == {"physicianName": "Dr. Thomas", "patientName": "Harpreet"}
    with client.websocket_connect("/ws/visit?role=screen") as tv:
        state = tv.receive_json()["payload"]
        assert (state["physicianName"], state["patientName"]) == ("Dr. Thomas", "Harpreet")


def test_set_names_keeps_a_name_left_out_and_clears_a_blank(client):
    with client.websocket_connect("/ws/visit?role=controller") as ctl:
        ctl.receive_json()
        set_names(ctl, physicianName="Dr. Thomas", patientName="Harpreet")
        ctl.receive_json()
        set_names(ctl, patientName="Harpreet Kaur")
        assert ctl.receive_json()["payload"] == {"physicianName": "Dr. Thomas", "patientName": "Harpreet Kaur"}
        set_names(ctl, physicianName="")
        assert ctl.receive_json()["payload"] == {"physicianName": None, "patientName": "Harpreet Kaur"}


@pytest.mark.parametrize("name", ["x" * 61, "Room 4"])
def test_set_names_rejects_long_or_numbered_names(client, name):
    with client.websocket_connect("/ws/visit?role=controller") as ctl:
        ctl.receive_json()
        set_names(ctl, physicianName=name)
        event = ctl.receive_json()
        assert event["type"] == "error" and event["payload"]["command"] == "visit.set_names"
    assert client.app.state.hub.visit.physician_name is None


def test_set_names_mid_visit_leaves_earlier_turns_alone(client):
    with client.websocket_connect("/ws/visit?role=controller") as ctl:
        ctl.receive_json()
        submit(ctl, "physician", "en-CA", "Hello.")
        before = drain_until(ctl, "turn.result")[-1]["payload"]
        set_names(ctl, patientName="Harpreet")
        assert drain_until(ctl, "visit.names")[-1]["payload"]["patientName"] == "Harpreet"
    with client.websocket_connect("/ws/visit?role=screen") as tv:
        assert tv.receive_json()["payload"]["turns"][0] == before


def test_screen_cannot_set_names(client):
    with client.websocket_connect("/ws/visit?role=screen") as tv:
        tv.receive_json()
        set_names(tv, patientName="Someone")
    assert client.app.state.hub.visit.patient_name is None


def test_visit_names_reach_the_translate_prompt_mdd_004(kb):
    model = ScriptedModel(
        {"translate": fake_model.translate, "tone_check": fake_model.tone_check, "empathy": fake_model.empathy}
    )
    with (
        ConsentedClient(create_app(model=model, settings=SETTINGS, kb=kb)) as c,
        c.websocket_connect("/ws/visit?role=controller") as ctl,
    ):
        ctl.receive_json()
        set_names(ctl, physicianName="Dr. Thomas", patientName="Harpreet")
        ctl.receive_json()
        submit(ctl, "physician", "en-CA", "Hello.")
        drain_until(ctl, "turn.result")
    user = next(u for purpose, u in model.calls if purpose == "translate")
    assert fake_model.field(user, "speaker_name") == "Dr. Thomas"
    assert fake_model.field(user, "listener_name") == "Harpreet"


# ---------- introduction (CDR-003, MDD-004) ----------


def command(ws, type_, **payload):
    ws.send_json({"type": type_, "payload": payload})


def lines_of(events, purpose):
    return [e["payload"] for e in events if e["type"] == "interpreter.line" and e["payload"]["purpose"] == purpose]


def test_introduction_asks_physician_then_patient_then_welcomes(client):
    with (
        client.websocket_connect("/ws/visit?role=controller") as ctl,
        client.websocket_connect("/ws/visit?role=screen") as tv,
    ):
        ctl.receive_json(), tv.receive_json()
        command(ctl, "visit.start_introduction")
        events = drain_until(ctl, "interpreter.line")
        intro = lines_of(events, "introduction")[0]
        assert [line["language"] for line in intro["lines"]] == ["en-CA", "pa-IN"]
        events = drain_until(ctl, "interpreter.line")
        assert events[0]["payload"]["introduction"] == "asking_physician"
        assert lines_of(events, "ask_physician_name")[0]["lines"][0]["language"] == "en-CA"

        command(ctl, "visit.name_reply", role="physician", text="I'm Dr. Thomas.")
        proposed = drain_until(ctl, "visit.name_proposed")[-1]["payload"]
        assert proposed == {"role": "physician", "name": "Dr. Thomas"}
        command(ctl, "visit.name_confirm", role="physician")
        events = drain_until(ctl, "interpreter.line")
        assert events[0]["payload"]["physicianName"] == "Dr. Thomas"
        ask = lines_of(events, "ask_patient_name")[0]["lines"][0]
        assert ask["language"] == "pa-IN" and "Dr. Thomas" in ask["text"]

        command(ctl, "visit.name_reply", role="patient", text="Harpreet")
        drain_until(ctl, "visit.name_proposed")
        command(ctl, "visit.name_confirm", role="patient")
        welcome = lines_of(drain_until(ctl, "interpreter.line"), "welcome")[0]
        assert "Harpreet" in welcome["lines"][0]["text"]

        tv_events = drain_until(tv, "interpreter.line")
        while len(lines_of(tv_events, "welcome")) == 0:
            tv_events += drain_until(tv, "interpreter.line")
        assert "visit.name_proposed" not in types(tv_events)  # proposals stay on the controller
    assert client.app.state.hub.visit.introduction == "done"


def test_introduction_skips_a_saved_physician_name(client):
    with client.websocket_connect("/ws/visit?role=controller") as ctl:
        ctl.receive_json()
        set_names(ctl, physicianName="Dr. Thomas")
        ctl.receive_json()
        command(ctl, "visit.start_introduction")
        drain_until(ctl, "interpreter.line")  # introduction
        events = drain_until(ctl, "interpreter.line")
        assert events[0]["payload"]["introduction"] == "asking_patient"
        assert lines_of(events, "ask_patient_name")


def test_rejected_name_asks_again_and_typed_name_answers(client):
    with client.websocket_connect("/ws/visit?role=controller") as ctl:
        ctl.receive_json()
        command(ctl, "visit.start_introduction")
        drain_until(ctl, "interpreter.line")
        drain_until(ctl, "interpreter.line")
        command(ctl, "visit.name_reply", role="physician", text="Dr. Tomas")
        drain_until(ctl, "visit.name_proposed")
        command(ctl, "visit.name_reject", role="physician")
        assert lines_of(drain_until(ctl, "interpreter.line"), "ask_physician_name")
        set_names(ctl, physicianName="Dr. Thomas")
        events = drain_until(ctl, "interpreter.line")
        assert events[0]["payload"] == {"physicianName": "Dr. Thomas", "patientName": None}
        assert lines_of(events, "ask_patient_name")
    assert client.app.state.hub.visit.proposed_names == {}


def test_reply_without_a_name_is_an_error(client):
    with client.websocket_connect("/ws/visit?role=controller") as ctl:
        ctl.receive_json()
        command(ctl, "visit.start_introduction")
        drain_until(ctl, "interpreter.line")
        drain_until(ctl, "interpreter.line")
        command(ctl, "visit.name_reply", role="physician", text="")
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "visit.name_reply"
        command(ctl, "visit.name_reply", role="patient", text="Harpreet")  # not the role being asked
        assert "patient" in drain_until(ctl, "error")[-1]["payload"]["message"]


def test_first_turn_skips_the_introduction_and_it_cannot_start_after(client):
    with client.websocket_connect("/ws/visit?role=controller") as ctl:
        ctl.receive_json()
        submit(ctl, "physician", "en-CA", "Hello.")
        events = drain_until(ctl, "turn.result")
        assert events[0]["type"] == "visit.state" and events[0]["payload"]["introduction"] == "skipped"
        command(ctl, "visit.start_introduction")
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "visit.start_introduction"


def test_turn_part_way_through_skips_the_rest(client):
    with client.websocket_connect("/ws/visit?role=controller") as ctl:
        ctl.receive_json()
        command(ctl, "visit.start_introduction")
        drain_until(ctl, "interpreter.line")
        drain_until(ctl, "interpreter.line")
        submit(ctl, "physician", "en-CA", "Let's just start.")
        drain_until(ctl, "turn.result")
    assert client.app.state.hub.visit.introduction == "skipped"


def test_screen_cannot_drive_the_introduction(client):
    with client.websocket_connect("/ws/visit?role=screen") as tv:
        tv.receive_json()
        command(tv, "visit.start_introduction")
    assert client.app.state.hub.visit.introduction == "pending"


# ---------- test languages (TDM-003) ----------


def set_patient_language(ws, language):
    command(ws, "visit.set_languages", patientLanguage=language, physicianLanguage="en-CA")


def test_test_languages_are_refused_without_test_mode(kb):
    with make_client(kb, consent=False) as client:
        refuse_test_language(client)


def refuse_test_language(client):
    assert client.get("/api/health").json()["testLanguages"] is False
    with client.websocket_connect("/ws/visit?role=controller") as ctl:
        ctl.receive_json()
        set_patient_language(ctl, "si-LK")
        event = ctl.receive_json()
        assert event["type"] == "error" and "coming soon" in event["payload"]["message"]
    assert client.app.state.hub.visit.patient_language == "pa-IN"


def test_tamil_is_live_without_test_mode_tdm_004(kb):
    with make_client(kb, language="ta-LK") as client, client.websocket_connect("/ws/visit?role=controller") as ctl:
        assert client.get("/api/health").json()["testLanguages"] is False
        assert ctl.receive_json()["payload"]["patientLanguage"] == "ta-LK"
        submit(ctl, "physician", "en-CA", "Your blood sugar is too high.")
        caption = drain_until(ctl, "turn.result")[-1]["payload"]
        # A Tamil dose gets the same read-back as in Punjabi and French.
        submit(ctl, "physician", "en-CA", "Take metformin 500 mg twice a day.")
        drain_until(ctl, "turn.readback_required")
    assert caption["targetLanguage"] == "ta-LK" and "இரத்தச் சீனி அளவு" in caption["translation"]


def test_test_mode_allows_sinhala_and_relays_it(kb):
    settings = Settings(translator="fake", azure_speech_key=None, azure_speech_region=None, test_languages=True)
    model = ScriptedModel(
        {"translate": fake_model.translate, "tone_check": fake_model.tone_check, "empathy": fake_model.empathy}
    )
    with ConsentedClient(create_app(model=model, settings=settings, kb=kb), language="si-LK") as c:
        assert c.get("/api/health").json()["testLanguages"] is True
        with c.websocket_connect("/ws/visit?role=controller") as ctl:
            assert ctl.receive_json()["payload"]["patientLanguage"] == "si-LK"
            submit(ctl, "physician", "en-CA", "Your high blood pressure can be treated.")
            caption = drain_until(ctl, "turn.result")[-1]["payload"]
            # A dose in Sinhala gets the same read-back as in Punjabi and French.
            submit(ctl, "physician", "en-CA", "Take amlodipine 5 mg once a day.")
            drain_until(ctl, "turn.readback_required")
    assert caption["targetLanguage"] == "si-LK" and caption["translation"].startswith("[si-LK]")
    user = next(u for purpose, u in model.calls if purpose == "translate")
    assert "අධික රුධිර පීඩනය" in fake_model.field(user, "glossary")  # the Sinhala glossary reached the prompt


# ---------- voice playback (CDR-004) ----------


def play(ws, type_, speech_id, language):
    command(ws, type_, speechId=speech_id, language=language)


def spoken_turn(ctl, tv):
    """A settled final physician turn, spoken in Punjabi; a physician turn sends no empathy nudge to interleave."""
    submit(ctl, "physician", "en-CA", "Hello.")
    turn_id = drain_until(ctl, "turn.result")[-1]["payload"]["turnId"]
    # The settled turn is chained, so record.integrity follows it on every role (CDR-006).
    drain_until(ctl, "record.integrity"), drain_until(tv, "record.integrity")
    return turn_id


def speaking(event):
    assert event["type"] == "voice.speaking", event["type"]
    return event["payload"]


def nothing_published(ctl, tv):
    """A marker event both roles receive; if voice.speaking had been published, it would arrive first."""
    set_names(ctl, patientName="Marker")
    assert tv.receive_json()["type"] == "visit.names"
    assert drain_until(ctl, "visit.names")[-1]["type"] == "visit.names"


def test_voice_playback_reaches_every_role_and_ends(client):
    with (
        client.websocket_connect("/ws/visit?role=controller") as ctl,
        client.websocket_connect("/ws/visit?role=screen") as tv,
    ):
        ctl.receive_json(), tv.receive_json()
        turn_id = spoken_turn(ctl, tv)
        play(ctl, "voice.started", turn_id, "pa-IN")
        assert speaking(tv.receive_json()) == {"speaking": True, "speechId": turn_id, "language": "pa-IN"}
        assert speaking(ctl.receive_json())["speaking"] is True
        play(ctl, "voice.ended", turn_id, "pa-IN")
        assert speaking(tv.receive_json()) == {"speaking": False, "speechId": None, "language": None}


def test_interpreter_lines_speak_back_to_back_and_a_stale_end_is_ignored(client):
    with (
        client.websocket_connect("/ws/visit?role=controller") as ctl,
        client.websocket_connect("/ws/visit?role=screen") as tv,
    ):
        ctl.receive_json(), tv.receive_json()
        command(ctl, "visit.start_introduction")
        line_id = lines_of(drain_until(tv, "interpreter.line"), "introduction")[0]["lineId"]
        play(ctl, "voice.started", line_id, "en-CA")
        assert speaking(drain_until(tv, "voice.speaking")[-1])["language"] == "en-CA"
        play(ctl, "voice.started", line_id, "pa-IN")  # the next language replaces the first
        assert speaking(tv.receive_json())["language"] == "pa-IN"
        play(ctl, "voice.ended", line_id, "en-CA")  # the queue reports the first end late
        play(ctl, "voice.ended", line_id, "pa-IN")
        assert speaking(tv.receive_json())["speaking"] is False  # the stale end published nothing


def test_a_repeated_start_publishes_nothing(client):
    with (
        client.websocket_connect("/ws/visit?role=controller") as ctl,
        client.websocket_connect("/ws/visit?role=screen") as tv,
    ):
        ctl.receive_json(), tv.receive_json()
        turn_id = spoken_turn(ctl, tv)
        play(ctl, "voice.started", turn_id, "pa-IN")
        assert speaking(tv.receive_json())["speaking"] is True
        play(ctl, "voice.started", turn_id, "pa-IN")
        play(ctl, "voice.ended", turn_id, "pa-IN")
        assert speaking(tv.receive_json())["speaking"] is False


def test_voice_started_is_refused_for_unknown_ids_wrong_languages_and_unconfirmed_doses(client):
    with (
        client.websocket_connect("/ws/visit?role=controller") as ctl,
        client.websocket_connect("/ws/visit?role=screen") as tv,
    ):
        ctl.receive_json(), tv.receive_json()
        turn_id = spoken_turn(ctl, tv)
        play(ctl, "voice.started", "unknown", "pa-IN")
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "voice.started"
        play(ctl, "voice.started", turn_id, "en-CA")  # spoken in Punjabi, not English
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "voice.started"

        submit(ctl, "physician", "en-CA", DOSE)
        dose_id = drain_until_stage(ctl, "awaiting_readback")[-1]["payload"]["turnId"]
        drain_until_stage(tv, "awaiting_readback")
        play(ctl, "voice.started", dose_id, "pa-IN")  # not confirmed yet
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "voice.started"
        ctl.send_json({"type": "turn.readback_reject", "payload": {"turnId": dose_id}})
        drain_until_stage(tv, "discarded")
        drain_until_stage(ctl, "discarded")
        play(ctl, "voice.started", dose_id, "pa-IN")  # rejected
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "voice.started"
        nothing_published(ctl, tv)


def test_voice_started_is_refused_for_a_blocked_turn(kb):
    def wrong(user):
        d = fake_model.translate(user)
        return Draft(**{**d.model_dump(), "translation": d.translation.replace("0.4", "4")})

    with (
        make_client(kb, translate=wrong) as client,
        client.websocket_connect("/ws/visit?role=controller") as ctl,
        client.websocket_connect("/ws/visit?role=screen") as tv,
    ):
        ctl.receive_json(), tv.receive_json()
        submit(ctl, "physician", "en-CA", DOSE)
        turn_id = drain_until(ctl, "turn.result")[-1]["payload"]["turnId"]
        drain_until(tv, "record.integrity")
        play(ctl, "voice.started", turn_id, "pa-IN")
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "voice.started"
        nothing_published(ctl, tv)


def test_voice_started_is_refused_for_an_escalated_turn(kb):
    def failing(user):
        return ToneCheck(meaning_preserved=True, certainty_preserved=False, warmth_preserved=True, issue="x")

    with (
        make_client(kb, tone_check=failing) as client,
        client.websocket_connect("/ws/visit?role=controller") as ctl,
        client.websocket_connect("/ws/visit?role=screen") as tv,
    ):
        ctl.receive_json(), tv.receive_json()
        submit(ctl, "physician", "en-CA", "This is very unlikely to be serious.")
        turn_id = drain_until(ctl, "turn.result")[-1]["payload"]["turnId"]
        drain_until(tv, "interpreter.escalation")
        drain_until(tv, "record.integrity")
        drain_until(ctl, "interpreter.escalation")
        play(ctl, "voice.started", turn_id, "pa-IN")
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "voice.started"
        nothing_published(ctl, tv)


def test_screen_cannot_report_voice_playback(client):
    with (
        client.websocket_connect("/ws/visit?role=controller") as ctl,
        client.websocket_connect("/ws/visit?role=screen") as tv,
    ):
        ctl.receive_json(), tv.receive_json()
        turn_id = spoken_turn(ctl, tv)
        play(tv, "voice.started", turn_id, "pa-IN")
        play(tv, "voice.ended", turn_id, "pa-IN")
        nothing_published(ctl, tv)
    assert client.app.state.hub.visit.speech is None


def test_controller_disconnect_mid_speech_clears_it(client):
    with (
        client.websocket_connect("/ws/visit?role=controller") as ctl,
        client.websocket_connect("/ws/visit?role=screen") as tv,
    ):
        ctl.receive_json(), tv.receive_json()
        turn_id = spoken_turn(ctl, tv)
        with client.websocket_connect("/ws/visit?role=controller") as laptop:
            laptop.receive_json()
            play(laptop, "voice.started", turn_id, "pa-IN")
            assert speaking(tv.receive_json())["speaking"] is True
            # Disconnect as a browser does; leaving the block would also cancel the server task mid-cleanup.
            laptop.close()
            assert speaking(tv.receive_json())["speaking"] is False


def test_speech_without_an_end_clears_after_the_ceiling(kb):
    with (
        make_client(kb, voice_ceiling_s=0.05) as client,
        client.websocket_connect("/ws/visit?role=controller") as ctl,
        client.websocket_connect("/ws/visit?role=screen") as tv,
    ):
        ctl.receive_json(), tv.receive_json()
        turn_id = spoken_turn(ctl, tv)
        play(ctl, "voice.started", turn_id, "pa-IN")
        assert speaking(tv.receive_json())["speaking"] is True
        assert speaking(tv.receive_json())["speaking"] is False  # no voice.ended was sent


def test_screen_connecting_mid_speech_sees_it_in_its_snapshot(client):
    with (
        client.websocket_connect("/ws/visit?role=controller") as ctl,
        client.websocket_connect("/ws/visit?role=screen") as tv,
    ):
        ctl.receive_json(), tv.receive_json()
        turn_id = spoken_turn(ctl, tv)
        play(ctl, "voice.started", turn_id, "pa-IN")
        tv.receive_json()
        with client.websocket_connect("/ws/visit?role=screen") as late:
            state = late.receive_json()
            assert state["payload"]["speaking"] == {"speaking": True, "speechId": turn_id, "language": "pa-IN"}
    with client.websocket_connect("/ws/visit?role=screen") as after:
        # The controller that started it has gone, so the speech ended with it.
        assert after.receive_json()["payload"]["speaking"]["speaking"] is False
