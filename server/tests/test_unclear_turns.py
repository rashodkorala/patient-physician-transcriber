"""Unclear turns and the per-speaker unclear streak on the visit channel (ADR-003 amended 2026-11-12, CDR-002, and
the `ask_to_repeat` line of CDR-003): a confidence failure after the retry is unclear, never spoken or shown as a
translation, and the interpreter asks the speaker to say it again in their language; the same speaker's third in a
row escalates with reason `low_confidence`, and a final or read-back-confirmed turn resets the streak."""

import pytest
from test_visit_channel import (
    DOSE,
    drain_until,
    drain_until_stage,
    kb,  # noqa: F401  (fixture)
    make_client,
    set_names,
    submit,
    types,
)
from test_voice import FakeVoice
from test_voice import make_client as make_voice_client
from visit_helpers import close, command, connect

from fake_model import MISMATCH_MARKER, TONE_MARKER, UNCLEAR_MARKER
from introduction import LINES

MUMBLED = f"ਮੈਨੂੰ ਕੱਲ੍ਹ ਤੋਂ ਚੱਕਰ ਆ ਰਹੇ ਹਨ। {UNCLEAR_MARKER}"
CLEAR = "ਮੈਨੂੰ ਕੱਲ੍ਹ ਤੋਂ ਚੱਕਰ ਆ ਰਹੇ ਹਨ।"


@pytest.fixture
def client(kb):  # noqa: F811
    with make_client(kb) as c:
        yield c


def settle(ctl, speaker="patient", language="pa-IN", text=MUMBLED, confidence=0.95):
    """One turn to its outcome on the controller: (analysis, caption, events after the caption up to the follow-up).

    The follow-up is the say-it-again line for an unclear turn, the offer for an escalated one, and the record's
    integrity otherwise.
    """
    submit(ctl, speaker, language, text, confidence)
    events = drain_until(ctl, "turn.result")
    analysis = next(e for e in events if e["type"] == "turn.analysis")["payload"]
    caption = events[-1]["payload"]
    follow = {"unclear": "interpreter.line", "escalated": "interpreter.escalation"}.get(caption["status"])
    after = drain_until(ctl, follow or "record.integrity")
    return analysis, caption, after


def streak(client):
    return dict(client.app.state.hub.visit.unclear_streak)


def has_key(obj, key) -> bool:
    if isinstance(obj, dict):
        return key in obj or any(has_key(v, key) for v in obj.values())
    if isinstance(obj, list):
        return any(has_key(v, key) for v in obj)
    return False


# ---------- the streak ----------


def test_unclear_unclear_then_escalated_with_low_confidence_cdr_002(client):
    sockets, (ctl, tv, review) = connect(client, "controller", "screen", "review")
    try:
        outcomes = []
        for _ in range(3):
            analysis, caption, after = settle(ctl)
            outcomes.append((analysis["status"], analysis["unclearStreak"], caption["status"]))
            if caption["status"] == "unclear":
                assert "interpreter.escalation" not in types(after)
        assert outcomes == [("unclear", 1, "unclear"), ("unclear", 2, "unclear"), ("escalated", 0, "escalated")]
        assert after[-1]["payload"]["reason"] == "low_confidence"
        assert streak(client)["patient"] == 0

        # The screen and the review phone get the captions and the offer, never the streak.
        public = [drain_until(ws, "interpreter.escalation") for ws in (tv, review)]
        for events in public:
            captions = [e["payload"] for e in events if e["type"] == "turn.result"]
            assert [c["status"] for c in captions] == ["unclear", "unclear", "escalated"]
            assert all(c["translation"] is None for c in captions)
            assert "turn.analysis" not in types(events)
            assert not has_key(events, "unclearStreak")
    finally:
        close(sockets)


def test_unclear_caption_has_no_translation_or_translated_values_cdr_002(client):
    sockets, (ctl, tv) = connect(client, "controller", "screen")
    try:
        analysis, caption, _ = settle(ctl, "physician", "en-CA", DOSE, confidence=0.4)
        # A matched dose below the confidence threshold is unclear, never read back (precedence, CDR-002).
        assert analysis["status"] == "unclear" and all(v["matched"] for v in analysis["criticalValues"])
        screen = drain_until(tv, "turn.result")[-1]["payload"]
        for c in (caption, screen):
            assert c["status"] == "unclear" and c["translation"] is None and c["toneLabel"] is None
            assert c["criticalValues"] == [] and c["glossaryUsed"] == [] and c["manner"] is None
            assert "unclearStreak" not in c
        assert "[pa-IN]" not in str(drain_until(tv, "interpreter.line"))
    finally:
        close(sockets)


def test_a_final_turn_between_resets_the_streak_adr_003(client):
    sockets, (ctl,) = connect(client, "controller")
    try:
        assert settle(ctl)[1]["status"] == "unclear"
        assert settle(ctl)[1]["status"] == "unclear"
        analysis, caption, _ = settle(ctl, text=CLEAR)
        assert caption["status"] == "final" and analysis["unclearStreak"] == 0
        analysis, caption, _ = settle(ctl)
        assert caption["status"] == "unclear" and analysis["unclearStreak"] == 1
    finally:
        close(sockets)


def test_a_blocked_turn_leaves_the_streak_adr_003(client):
    sockets, (ctl,) = connect(client, "controller")
    try:
        settle(ctl)
        analysis, caption, _ = settle(ctl, text=f"ਮੈਂ 58 ਸਾਲ ਦਾ ਹਾਂ। {MISMATCH_MARKER}")
        assert caption["status"] == "blocked" and analysis["unclearStreak"] == 1 and streak(client)["patient"] == 1
        assert settle(ctl)[1]["status"] == "unclear"
        _, caption, after = settle(ctl)
        assert caption["status"] == "escalated" and after[-1]["payload"]["reason"] == "low_confidence"
    finally:
        close(sockets)


def test_a_tone_only_failure_escalates_at_once_adr_003(client):
    sockets, (ctl,) = connect(client, "controller")
    try:
        settle(ctl)
        analysis, caption, after = settle(ctl, text=f"ਮੈਨੂੰ ਠੀਕ ਲੱਗਦਾ ਹੈ। {TONE_MARKER}")
        assert caption["status"] == "escalated" and after[-1]["payload"]["reason"] == "tone_failure"
        assert analysis["unclearStreak"] == 1 and streak(client)["patient"] == 1  # a tone escalation leaves it
    finally:
        close(sockets)


def test_streaks_are_per_speaker_and_a_confirmed_read_back_resets_cdr_002(client):
    sockets, (ctl,) = connect(client, "controller")
    try:
        settle(ctl)
        settle(ctl, "physician", "en-CA", "How are you feeling today?", confidence=0.4)
        assert streak(client) == {"patient": 1, "physician": 1, "companion": 0}
        submit(ctl, "physician", "en-CA", DOSE)
        turn_id = drain_until_stage(ctl, "awaiting_readback")[-1]["payload"]["turnId"]
        assert streak(client)["physician"] == 1  # waiting: not reset until confirmed
        command(ctl, "turn.readback_confirm", turnId=turn_id)
        drain_until(ctl, "turn.result")
        assert streak(client) == {"patient": 1, "physician": 0, "companion": 0}

        # A reloaded controller sees the streak; a screen's snapshot never does.
        with client.websocket_connect("/ws/visit?role=controller") as late:
            state = late.receive_json()["payload"]
            assert state["unclearStreak"] == {"patient": 1, "physician": 0, "companion": 0}
            confirmed = next(t for t in state["turns"] if t["turnId"] == turn_id)
            assert confirmed["unclearStreak"] == 0
        for role in ("screen", "review"):
            with client.websocket_connect(f"/ws/visit?role={role}") as late:
                assert not has_key(late.receive_json(), "unclearStreak")
    finally:
        close(sockets)


# ---------- the say-it-again line ----------


def test_ask_to_repeat_is_said_in_the_speakers_language_only_adr_003(client):
    sockets, (ctl, tv) = connect(client, "controller", "screen")
    try:
        _, _, after = settle(ctl)
        line = after[-1]["payload"]
        assert line["purpose"] == "ask_to_repeat"
        assert line["lines"] == [{"language": "pa-IN", "text": LINES["pa"]["ask_to_repeat"]}]
        assert drain_until(tv, "interpreter.line")[-1]["payload"] == line  # every role is told

        set_names(ctl, physicianName="Dr. Thomas", patientName="Harpreet")
        drain_until(ctl, "visit.names")
        named = settle(ctl)[2][-1]["payload"]
        assert named["lines"] == [
            {"language": "pa-IN", "text": LINES["pa"]["ask_to_repeat_named"].format(name="Harpreet")}
        ]
        physician = settle(ctl, "physician", "en-CA", "How are you feeling?", confidence=0.4)[2][-1]["payload"]
        assert physician["lines"] == [
            {"language": "en-CA", "text": "Sorry, Dr. Thomas, I did not catch that. Could you say it again?"}
        ]
    finally:
        close(sockets)


def test_speak_gate_serves_ask_to_repeat_in_the_speakers_language_only_adr_003(kb):  # noqa: F811
    voice = FakeVoice()
    with make_voice_client(kb, voice) as client, client.websocket_connect("/ws/visit?role=controller") as ctl:
        ctl.receive_json()
        submit(ctl, "patient", "pa-IN", MUMBLED)
        caption = drain_until(ctl, "turn.result")[-1]["payload"]
        line = drain_until(ctl, "interpreter.line")[-1]["payload"]
        assert client.get(f"/api/speech/{caption['turnId']}?language=en-CA").status_code == 404  # never the turn
        assert client.get(f"/api/speech/{line['lineId']}?language=en-CA").status_code == 404
        assert client.get(f"/api/speech/{line['lineId']}").status_code == 404
        assert client.get(f"/api/speech/{line['lineId']}?language=pa-IN").status_code == 200
    assert [(text, language) for text, language, _ in voice.said] == [(LINES["pa"]["ask_to_repeat"], "pa-IN")]


# ---------- the record ----------


def test_an_unclear_turn_is_chained_without_its_translation_and_is_a_gap_cdr_002(client):
    sockets, (ctl,) = connect(client, "controller")
    try:
        _, caption, _ = settle(ctl)
        visit = client.app.state.hub.visit
        turn = next(e.payload for e in visit.chain.entries if e.payload["entryId"] == caption["turnId"])
        assert turn["kind"] == "turn" and turn["body"]["settledAs"] == "unclear" and turn["body"]["status"] == "unclear"
        assert turn["body"]["translation"] is None and turn["body"]["criticalValues"] == []
        assert "unclearStreak" not in turn["body"] and "[en-CA]" not in str(turn)
        assert visit.integrity().status == "verified"
        # A gap in the note and summary sources, like a blocked turn; its words are never a source.
        snapshot = visit.freeze()
        assert caption["turnId"] in snapshot.untranslated_turn_ids
        assert "ਚੱਕਰ" not in str(snapshot.turns)
        # The line asking again is the interpreter's own, not a turn.
        assert not visit.spoken(caption["turnId"])
    finally:
        close(sockets)
