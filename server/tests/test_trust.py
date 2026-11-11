"""The trust advisor's code-decided parts (MDD-005, CDR-008): the reassurance rule, the understanding cues, the
cue bounds, and the visit's spoken order and trust timeline order. The model-facing half runs in
test_trust_channel.py against the scripted model."""

import asyncio
import json
from pathlib import Path

import pytest
from test_visit_channel import kb  # noqa: F401  (fixture)

from contracts import TRUST_CUE_MAX, EmpathyNudge, TrustUpdate, TurnResult
from llm import ScriptedModel
from trust import (
    CULTURE_CUE_ASK,
    CULTURE_SYSTEM,
    UNDERSTANDING_CUES,
    CultureCueDraft,
    SpokenTurn,
    TrustAdvisor,
    clip,
    nudge_cue,
    reassurance_landed,
    understanding_cue,
)
from visit_store import TurnRecord, Visit

PATIENT_WORRIED = SpokenTurn("patient", "worried", "plain")
PATIENT_CALM = SpokenTurn("patient", "calm", "plain")
COMPANION_WORRIED = SpokenTurn("companion", "worried", "plain")
PHYSICIAN_PLAIN = SpokenTurn("physician", "calm", "plain")
PHYSICIAN_REASSURING = SpokenTurn("physician", "calm", "reassuring")


@pytest.mark.parametrize(
    ("history", "speaker", "emotion", "expected"),
    [
        # Worry, reassurance, then calm or relief: landed.
        ([PATIENT_WORRIED, PHYSICIAN_REASSURING], "patient", "calm", True),
        ([PATIENT_WORRIED, PHYSICIAN_REASSURING], "patient", "relieved", True),
        # Worry, reassurance, still worried (or confused): not yet.
        ([PATIENT_WORRIED, PHYSICIAN_REASSURING], "patient", "worried", False),
        ([PATIENT_WORRIED, PHYSICIAN_REASSURING], "patient", "confused", False),
        # No earlier worry: no mark, however reassuring the physician was.
        ([PHYSICIAN_REASSURING], "patient", "calm", None),
        ([PATIENT_CALM, PHYSICIAN_REASSURING], "patient", "calm", None),
        # Worry without a reassuring, warm, gentle, or encouraging turn between: no mark.
        ([PATIENT_WORRIED, PHYSICIAN_PLAIN], "patient", "calm", None),
        ([PATIENT_WORRIED], "patient", "calm", None),
        # The reassurance must come after the worry, not before it.
        ([PHYSICIAN_REASSURING, PATIENT_WORRIED], "patient", "calm", None),
        # Every reassuring manner counts; every worry emotion counts.
        (
            [SpokenTurn("patient", "embarrassed", "plain"), SpokenTurn("physician", "calm", "warm")],
            "patient",
            "calm",
            True,
        ),
        (
            [SpokenTurn("patient", "in_pain", "plain"), SpokenTurn("physician", "calm", "gentle")],
            "patient",
            "relieved",
            True,
        ),
        (
            [SpokenTurn("patient", "confused", "plain"), SpokenTurn("physician", "calm", "encouraging")],
            "patient",
            "calm",
            True,
        ),
        # An earlier pair keeps counting through a later not-yet turn.
        ([PATIENT_WORRIED, PHYSICIAN_REASSURING, PATIENT_WORRIED], "patient", "calm", True),
        ([PATIENT_WORRIED, PHYSICIAN_REASSURING, PATIENT_WORRIED], "patient", "worried", False),
        # Once it has landed the pair is spent: later turns carry no mark until a new worry and a new reassurance.
        ([PATIENT_WORRIED, PHYSICIAN_REASSURING, PATIENT_CALM], "patient", "calm", None),
        ([PATIENT_WORRIED, PHYSICIAN_REASSURING, PATIENT_CALM], "patient", "worried", None),
        ([PATIENT_WORRIED, PHYSICIAN_REASSURING, PATIENT_CALM, PHYSICIAN_REASSURING], "patient", "worried", None),
        (
            [PATIENT_WORRIED, PHYSICIAN_REASSURING, PATIENT_CALM, PATIENT_WORRIED, PHYSICIAN_REASSURING],
            "patient",
            "calm",
            True,
        ),
        # A companion never carries the mark, and a companion's worry is not the patient's.
        ([PATIENT_WORRIED, PHYSICIAN_REASSURING], "companion", "calm", None),
        ([COMPANION_WORRIED, PHYSICIAN_REASSURING], "patient", "calm", None),
        # A physician turn never carries it.
        ([PATIENT_WORRIED, PHYSICIAN_REASSURING], "physician", "calm", None),
        ([], "patient", "calm", None),
    ],
)
def test_reassurance_landed_rule_cdr_008(history, speaker, emotion, expected):
    assert reassurance_landed(history, speaker, emotion) is expected


def test_reassurance_landed_resets_once_it_has_landed_cdr_008():
    """Worried, reassuring, calm (true), calm (null), worried (null): the mark resets once it has landed."""
    visit = [
        (SpokenTurn("patient", "worried", "plain"), None),
        (SpokenTurn("physician", "calm", "reassuring"), None),
        (SpokenTurn("patient", "calm", "plain"), True),
        (SpokenTurn("patient", "calm", "plain"), None),
        (SpokenTurn("patient", "worried", "plain"), None),
    ]
    marks = [
        reassurance_landed([t for t, _ in visit[:i]], turn.speaker, turn.emotion) for i, (turn, _) in enumerate(visit)
    ]
    assert marks == [expected for _, expected in visit]


# ---------- spoken order and the trust timeline's order (CDR-008) ----------


def turn_result(turn_id: str, speaker: str, emotion: str, manner: str, status: str = "final") -> TurnResult:
    fixture = json.loads((Path(__file__).parent / "fixtures" / "turn_result.json").read_text())
    language = {"physician": ("en-CA", "pa-IN")}.get(speaker, ("pa-IN", "en-CA"))
    return TurnResult.model_validate(fixture).model_copy(
        update={
            "turn_id": turn_id,
            "speaker": speaker,
            "source_language": language[0],
            "target_language": language[1],
            "emotion": emotion,
            "manner": manner,
            "status": status,
        }
    )


def settle(visit: Visit, turn_id: str, readback_confirmed: bool = False) -> None:
    record = visit.turns[turn_id]
    record.settled, record.readback_confirmed = True, readback_confirmed
    visit.append_turn(turn_id)


def test_spoken_history_follows_confirmation_order_not_submission_order_cdr_008():
    """A reassuring physician dose turn confirmed after a patient turn was spoken is in the history after it."""
    visit = Visit()
    # Submitted in this order: a worried patient turn, a reassuring dose (held for read-back), then a calm patient
    # turn that is spoken while the dose waits; the dose is confirmed (spoken) last.
    for turn_id, speaker, emotion, manner, status in [
        ("worried", "patient", "worried", "plain", "final"),
        ("dose", "physician", "calm", "reassuring", "readback_required"),
        ("calm", "patient", "calm", "plain", "final"),
        ("after", "patient", "calm", "plain", "final"),
    ]:
        visit.turns[turn_id] = TurnRecord(
            result=turn_result(turn_id, speaker, emotion, manner, status), speaker=speaker, source_text="", stage="x"
        )
    settle(visit, "worried")
    settle(visit, "calm")
    settle(visit, "dose", readback_confirmed=True)
    assert visit.settled_order == ["worried", "calm", "dose"]
    assert visit.last_settled_turn_id() == "dose"
    # The calm turn was spoken before the reassurance, so it has no mark ...
    assert [r.turn_id for r in visit.spoken_results_before("calm")] == ["worried"]
    # ... and a turn spoken after the confirmation has the dose in its history, after the calm turn.
    history = visit.spoken_results_before("after")
    assert [r.turn_id for r in history] == ["worried", "calm", "dose"]
    turns = [SpokenTurn(r.speaker, r.emotion, r.manner) for r in history]
    assert reassurance_landed(turns, "patient", "calm") is True


def trust_for(turn_id: str | None, signal: str | None = None) -> TrustUpdate:
    return TrustUpdate(
        turn_id=turn_id,
        speaker=None if signal else "patient",
        emotion=None if signal else "calm",
        manner=None if signal else "plain",
        reassurance_landed=None,
        signal=signal,
        cue=None,
        at="2026-11-11T10:00:00+00:00",
    )


def test_trust_timeline_is_kept_in_spoken_order_however_late_an_update_arrives_cdr_008():
    visit = Visit()
    for turn_id in ("a", "b", "c"):
        visit.turns[turn_id] = TurnRecord(
            result=turn_result(turn_id, "patient", "calm", "plain"), speaker="patient", source_text="", stage="x"
        )
    settle(visit, "a")
    settle(visit, "b")
    # A signal before any turn sorts first; signals after a turn sort after that turn's update.
    visit.add_trust(trust_for("b"))
    visit.add_trust(trust_for("b", "not_understood"))
    visit.add_trust(trust_for(None, "slower"))
    settle(visit, "c")
    visit.add_trust(trust_for("c"))
    visit.add_trust(trust_for("c", "repeat"))
    # Turn a's advisor returned last: its update still lands in a's place, before b's update and b's signal.
    visit.add_trust(trust_for("a"))
    visit.add_trust(trust_for("a", "slower"))
    assert [(u.turn_id, u.signal) for u in visit.trust] == [
        (None, "slower"),
        ("a", None),
        ("a", "slower"),
        ("b", None),
        ("b", "not_understood"),
        ("c", None),
        ("c", "repeat"),
    ]


def test_understanding_cues_are_fixed_english_within_bounds_cdr_008():
    assert set(UNDERSTANDING_CUES) == {"not_understood", "slower", "repeat"}
    for signal in UNDERSTANDING_CUES:
        cue = understanding_cue(signal)
        assert cue.kind == "understanding" and cue.text == UNDERSTANDING_CUES[signal]
        assert 0 < len(cue.text) <= TRUST_CUE_MAX
    assert understanding_cue("not_understood").text.startswith("Say it another way")


def test_nudge_cue_carries_the_suggestion_as_reassurance_cdr_008():
    nudge = EmpathyNudge(
        turn_id="t1", emotion="worried", suggestion="  Acknowledge  the worry. ", phrase="p", phrase_language="en-CA"
    )
    cue = nudge_cue(nudge)
    assert cue is not None and cue.kind == "reassurance" and cue.text == "Acknowledge the worry."
    assert nudge_cue(nudge.model_copy(update={"suggestion": "   "})) is None


def test_culture_cue_is_clipped_to_the_contract_and_null_means_none_cdr_008(kb):  # noqa: F811
    long = ScriptedModel({"trust": lambda user: CultureCueDraft(cue="x" * 500)})
    cue = asyncio.run(TrustAdvisor(long, kb).culture_cue("How much do you drink?", "pa-IN"))
    assert cue is not None and cue.kind == "culture" and len(cue.text) == TRUST_CUE_MAX
    quiet = ScriptedModel({"trust": lambda user: CultureCueDraft(cue=None)})
    assert asyncio.run(TrustAdvisor(quiet, kb).culture_cue("How long has it hurt?", "pa-IN")) is None
    # The advisor gives the model the retrieved tone and culture guidance for the patient's language.
    user = long.calls[0][1]
    assert "<speaker>physician</speaker>" in user and "<guidance>" in user and "Punjabi" in user


def test_long_cue_is_cut_at_the_last_sentence_end_before_the_limit_cdr_008():
    first = "This question may carry shame in the patient's culture."
    second = "Say why it matters for their care, and ask without judgement, in private, and with " + "care " * 30
    cut = clip(f"{first} {second}")
    assert cut == first and len(cut) <= TRUST_CUE_MAX


def test_long_cue_without_a_sentence_end_is_cut_at_a_word_boundary_cdr_008():
    text = "Ask about alcohol gently " + "and explain why it matters " * 10
    cut = clip(text)
    assert len(cut) <= TRUST_CUE_MAX and not cut.endswith(" ")
    assert text.startswith(cut) and text[len(cut)] == " "  # it stopped at the end of a whole word
    # A cue within the limit is untouched, and the live advisor's cue goes through the same cut.
    assert clip("Short and kind.") == "Short and kind."


def test_live_culture_cue_is_cut_cleanly_through_the_advisor_cdr_008(kb):  # noqa: F811
    words = "Say why the question matters for their care and ask without judgement " * 5
    model = ScriptedModel({"trust": lambda user: CultureCueDraft(cue=words)})
    cue = asyncio.run(TrustAdvisor(model, kb).culture_cue("How much do you drink?", "pa-IN"))
    assert cue is not None and len(cue.text) <= TRUST_CUE_MAX and words.startswith(cue.text)
    assert words[len(cue.text)] == " "


def test_culture_prompt_asks_for_short_cultural_cues_without_guessed_gender_cdr_008():
    assert CULTURE_CUE_ASK < TRUST_CUE_MAX and f"at most {CULTURE_CUE_ASK} characters" in CULTURE_SYSTEM
    assert "one or two short sentences" in CULTURE_SYSTEM
    assert "Never guess anyone's gender from a name" in CULTURE_SYSTEM and '"they"' in CULTURE_SYSTEM
    assert "never clinical advice" in CULTURE_SYSTEM and "never what the tests or results show" in CULTURE_SYSTEM
