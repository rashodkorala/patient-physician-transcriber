"""Visit channel tests: role routing, snapshots, languages, read-back, blocking, escalation,
and empathy nudges, run against the full turn graph with a scripted model (CDR-001, CDR-002)."""

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


def make_client(kb, translate=None, tone_check=None):
    model = ScriptedModel(
        {
            "analyse": fake_model.analyse,
            "translate": translate or fake_model.translate,
            "tone_check": tone_check or fake_model.tone_check,
            "empathy": fake_model.empathy,
        }
    )
    return TestClient(create_app(model=model, settings=SETTINGS, kb=kb))


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
        assert {"analysing", "checking_glossary", "translating", "verifying"} <= set(stages)
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


def test_set_languages_before_first_turn_then_rejected(client):
    with client.websocket_connect("/ws/visit?role=controller") as ctl:
        ctl.receive_json()
        ctl.send_json(
            {"type": "visit.set_languages", "payload": {"patientLanguage": "fr-CA", "physicianLanguage": "en-CA"}}
        )
        assert ctl.receive_json()["payload"]["patientLanguage"] == "fr-CA"
        submit(ctl, "patient", "fr-CA", "Bonjour")
        drain_until(ctl, "turn.result")
        ctl.send_json(
            {"type": "visit.set_languages", "payload": {"patientLanguage": "pa-IN", "physicianLanguage": "en-CA"}}
        )
        err = drain_until(ctl, "error")[-1]
        assert err["payload"]["command"] == "visit.set_languages"


def test_screen_cannot_send_controller_commands(client):
    with (
        client.websocket_connect("/ws/visit?role=screen") as tv,
        client.websocket_connect("/ws/visit?role=controller") as ctl,
    ):
        tv.receive_json(), ctl.receive_json()
        submit(tv, "patient", "pa-IN", "x")
        ctl.send_json(
            {"type": "visit.set_languages", "payload": {"patientLanguage": "fr-CA", "physicianLanguage": "en-CA"}}
        )
        assert ctl.receive_json()["type"] == "visit.state"  # no turn exists, so the screen's submit was ignored


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
    failing = lambda user: ToneCheck(certainty_preserved=False, warmth_preserved=True, issue="x")  # noqa: E731
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
