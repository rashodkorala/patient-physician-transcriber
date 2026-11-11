"""The trust advisor's code-decided parts (MDD-005, CDR-008): the reassurance rule, the understanding cues, and the
cue bounds. The model-facing half runs in test_trust_channel.py against the scripted model."""

import asyncio

import pytest
from test_visit_channel import kb  # noqa: F401  (fixture)

from contracts import TRUST_CUE_MAX, EmpathyNudge
from llm import ScriptedModel
from trust import (
    UNDERSTANDING_CUES,
    CultureCueDraft,
    SpokenTurn,
    TrustAdvisor,
    nudge_cue,
    reassurance_landed,
    understanding_cue,
)

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
