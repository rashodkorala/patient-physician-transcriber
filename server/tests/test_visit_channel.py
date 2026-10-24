"""Visit channel tests: role routing, snapshots, languages, and the week 1 turn path (CDR-001)."""

import pytest
from fastapi.testclient import TestClient

from config import Settings
from main import create_app
from translate import FakeTranslator

SETTINGS = Settings(translator="fake", azure_speech_key=None, azure_speech_region=None)
PRIVATE_KEYS = {"emotion", "certainty", "backTranslation"}


@pytest.fixture
def client():
    return TestClient(create_app(translator=FakeTranslator(), settings=SETTINGS))


def drain_until(ws, event_type):
    """Read events until one of event_type arrives; return all events read."""
    seen = []
    while True:
        event = ws.receive_json()
        seen.append(event)
        if event["type"] == event_type:
            return seen


def contains_private(obj) -> bool:
    if isinstance(obj, dict):
        return bool(PRIVATE_KEYS & obj.keys()) or any(contains_private(v) for v in obj.values())
    if isinstance(obj, list):
        return any(contains_private(v) for v in obj)
    return False


def test_connect_sends_role_filtered_state(client):
    with client.websocket_connect("/ws/visit?role=controller") as ctl, client.websocket_connect("/ws/visit?role=screen") as tv:
        ctl_state = ctl.receive_json()
        tv_state = tv.receive_json()
        assert ctl_state["type"] == tv_state["type"] == "visit.state"
        assert "nudges" in ctl_state["payload"]
        assert "nudges" not in tv_state["payload"]
        assert tv_state["payload"]["patientLanguage"] == "pa-IN"


def test_typed_patient_turn_reaches_screen_without_private_fields(client):
    with client.websocket_connect("/ws/visit?role=controller") as ctl, client.websocket_connect("/ws/visit?role=screen") as tv:
        ctl.receive_json(), tv.receive_json()
        ctl.send_json({"type": "turn.submit", "payload": {
            "speaker": "patient", "language": "pa-IN", "text": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ", "recognitionConfidence": 0.9}})

        ctl_events = drain_until(ctl, "turn.result")
        tv_events = drain_until(tv, "turn.result")

        assert [e["type"] for e in ctl_events] == ["turn.started", "turn.status", "turn.analysis", "turn.result"]
        assert [e["type"] for e in tv_events] == ["turn.started", "turn.status", "turn.result"]
        caption = tv_events[-1]["payload"]
        assert caption["sourceText"] == "ਸਤ ਸ੍ਰੀ ਅਕਾਲ"
        assert caption["translation"] == "[en-CA] ਸਤ ਸ੍ਰੀ ਅਕਾਲ"
        assert caption["targetLanguage"] == "en-CA"
        assert not any(contains_private(e) for e in tv_events)
        # seq has no gaps on the screen, even though the controller got an extra event.
        assert [e["seq"] for e in tv_events] == [2, 3, 4]


def test_screen_connecting_later_gets_settled_turns_only(client):
    with client.websocket_connect("/ws/visit?role=controller") as ctl:
        ctl.receive_json()
        ctl.send_json({"type": "turn.submit", "payload": {
            "speaker": "physician", "language": "en-CA", "text": "Hello", "recognitionConfidence": 0.95}})
        drain_until(ctl, "turn.result")
    with client.websocket_connect("/ws/visit?role=screen") as tv:
        state = tv.receive_json()
        assert state["type"] == "visit.state"
        assert state["payload"]["turns"][0]["translation"] == "[pa-IN] Hello"
        assert not contains_private(state)


def test_set_languages_before_first_turn_then_rejected(client):
    with client.websocket_connect("/ws/visit?role=controller") as ctl:
        ctl.receive_json()
        ctl.send_json({"type": "visit.set_languages", "payload": {"patientLanguage": "fr-CA", "physicianLanguage": "en-CA"}})
        state = ctl.receive_json()
        assert state["type"] == "visit.state" and state["payload"]["patientLanguage"] == "fr-CA"

        ctl.send_json({"type": "turn.submit", "payload": {
            "speaker": "patient", "language": "fr-CA", "text": "Bonjour", "recognitionConfidence": 0.9}})
        drain_until(ctl, "turn.result")

        ctl.send_json({"type": "visit.set_languages", "payload": {"patientLanguage": "pa-IN", "physicianLanguage": "en-CA"}})
        err = ctl.receive_json()
        assert err["type"] == "error" and err["payload"]["command"] == "visit.set_languages"


def test_screen_cannot_send_controller_commands(client):
    with client.websocket_connect("/ws/visit?role=screen") as tv, client.websocket_connect("/ws/visit?role=controller") as ctl:
        tv.receive_json(), ctl.receive_json()
        tv.send_json({"type": "turn.submit", "payload": {
            "speaker": "patient", "language": "pa-IN", "text": "x", "recognitionConfidence": 0.9}})
        # Nothing happens: the controller then sets languages freely because no turn exists.
        ctl.send_json({"type": "visit.set_languages", "payload": {"patientLanguage": "fr-CA", "physicianLanguage": "en-CA"}})
        assert ctl.receive_json()["type"] == "visit.state"


def test_errors_reach_controller_only(client):
    with client.websocket_connect("/ws/visit?role=controller") as ctl, client.websocket_connect("/ws/visit?role=screen") as tv:
        ctl.receive_json(), tv.receive_json()
        ctl.send_json({"type": "turn.submit", "payload": {
            "speaker": "patient", "language": "fr-CA", "text": "x", "recognitionConfidence": 0.9}})
        assert ctl.receive_json()["type"] == "error"
        ctl.send_json({"type": "visit.set_languages", "payload": {"patientLanguage": "fr-CA", "physicianLanguage": "en-CA"}})
        assert ctl.receive_json()["type"] == "visit.state"
        # The screen's next event is the state broadcast, not the earlier error.
        assert tv.receive_json()["type"] == "visit.state"


def test_speech_token_unconfigured_returns_503(client):
    response = client.get("/api/speech-token")
    assert response.status_code == 503
