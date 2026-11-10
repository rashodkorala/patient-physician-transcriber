"""Shared helpers for the explain-back, correction, tamper, note, and summary channel tests (CDR-005, CDR-006,
CDR-007, TDM-005): connections, a Punjabi plan with real translations, and role-leak checks."""

from test_visit_channel import drain_until, drain_until_stage, set_names, submit

import fake_model
from graph.turn_graph import Draft

PLAN_EN = "Take metformin 500 milligrams twice a day."
PLAN_PA = "ਮੈਟਫਾਰਮਿਨ 500 ਮਿਲੀਗ੍ਰਾਮ ਦਿਨ ਵਿੱਚ ਦੋ ਵਾਰ ਲਓ।"
# Patient lines, as said in Punjabi, and the English spoken to the physician.
SAID_DOSE_ONLY = ("ਮੈਟਫਾਰਮਿਨ 500 ਮਿਲੀਗ੍ਰਾਮ ਲੈਣੀ ਹੈ।", "I take metformin 500 milligrams.")
SAID_ONCE_A_DAY = ("ਮੈਟਫਾਰਮਿਨ 500 ਮਿਲੀਗ੍ਰਾਮ ਦਿਨ ਵਿੱਚ ਇੱਕ ਵਾਰ ਲੈਣੀ ਹੈ।", "I take metformin 500 milligrams once a day.")
SAID_IN_FULL = ("ਮੈਟਫਾਰਮਿਨ 500 ਮਿਲੀਗ੍ਰਾਮ ਦਿਨ ਵਿੱਚ ਦੋ ਵਾਰ ਲੈਣੀ ਹੈ।", "I take metformin 500 milligrams twice a day.")
CHEST = ("ਮੇਰੀ ਛਾਤੀ ਵਿੱਚ ਦਰਦ ਹੈ।", "I have pain in my chest.")
CHEST_CORRECTED = ("ਮੇਰੀ ਖੱਬੀ ਬਾਂਹ ਵਿੱਚ ਦਰਦ ਹੈ।", "I have pain in my left arm.")
TRANSLATIONS = {
    PLAN_EN: PLAN_PA,
    **dict([SAID_DOSE_ONLY, SAID_ONCE_A_DAY, SAID_IN_FULL, CHEST, CHEST_CORRECTED]),
}
PRIVATE_KEYS = {
    "emotion",
    "certainty",
    "backTranslation",
    "confidence",
    "toneTags",
    "nudges",
    "analysis",
    "items",
    "explainBackResults",
    "note",
    "noteStale",
    "summaryChecks",
    "mismatches",
    "detail",
    "tamper",
    "injection",
    "escalations",
}
PRIVATE_EVENTS = {
    "turn.analysis",
    "explainback.result",
    "segment.analysis",
    "demo.tamper_state",
    "note.status",
    "note.ready",
    "summary.check",
    "summary.speak",
    "error",
}


def translate(user: str) -> Draft:
    """The faithful fake, with real Punjabi and English for the lines these tests speak."""
    draft = fake_model.translate(user)
    text = fake_model.field(user, "utterance")
    if text in TRANSLATIONS:
        return draft.model_copy(update={"translation": TRANSLATIONS[text]})
    return draft


def leaks(obj) -> set[str]:
    """Every private key anywhere in a payload, except a null `detail` (summary.status keeps the field)."""
    found: set[str] = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in PRIVATE_KEYS and not (key == "detail" and value is None):
                found.add(key)
            found |= leaks(value)
    elif isinstance(obj, list):
        for value in obj:
            found |= leaks(value)
    return found


def assert_public(events) -> None:
    for event in events:
        assert event["type"] not in PRIVATE_EVENTS, event["type"]
        assert not leaks(event["payload"]), (event["type"], leaks(event["payload"]))


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
    """A public event every role receives; everything published before it has arrived by then."""
    set_names(ctl, patientName="Marker")
    return drain_until(ctl, "visit.names"), [drain_until(ws, "visit.names") for ws in others]


def speak_plan(ctl, text=PLAN_EN) -> str:
    """The physician gives a dose, the read-back is confirmed, and the turn is spoken; returns its turn id."""
    submit(ctl, "physician", "en-CA", text)
    turn_id = drain_until_stage(ctl, "awaiting_readback")[-1]["payload"]["turnId"]
    command(ctl, "turn.readback_confirm", turnId=turn_id)
    caption = drain_until(ctl, "turn.result")[-1]["payload"]
    assert caption["readbackConfirmed"] is True
    return turn_id


def patient_says(ctl, line) -> dict:
    """A patient turn; returns its caption."""
    submit(ctl, "patient", "pa-IN", line[0])
    return drain_until(ctl, "turn.result")[-1]["payload"]


def visit(client):
    return client.app.state.hub.visit


def entries(client):
    return [e.payload for e in visit(client).chain.entries]


def kinds(client):
    return [e["kind"] for e in entries(client)]
