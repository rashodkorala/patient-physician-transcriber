"""A frightened patient is treated as a worried one for the empathy nudge and the reassurance mark (CDR-008, amended
2026-11-16 for MDD-006 decision 8; affect-in-words task 10.4)."""

import asyncio

from test_visit_channel import kb  # noqa: F401  (fixture)

import fake_model
from contracts import EmpathyNudge
from llm import ScriptedModel
from trust import NUDGE_EMOTIONS, SpokenTurn, TrustAdvisor, reassurance_landed


def test_frightened_patient_turn_gets_the_empathy_nudge_cdr_008(kb):  # noqa: F811
    model = ScriptedModel({"trust": fake_model.trust})
    advisor = TrustAdvisor(model, kb)
    nudge = asyncio.run(advisor.nudge("t1", "frightened", "They are asking whether they will die like their mother."))
    assert isinstance(nudge, EmpathyNudge) and nudge.emotion == "frightened" and nudge.phrase
    # The reviewed bank has no entry tagged frightened; retrieval is by meaning, not filtered by emotion, so the
    # advisor still gets candidates and never sends an empty list.
    (_, user), *_ = model.calls
    assert "<emotion>frightened</emotion>" in user
    assert fake_model.field(user, "candidates").strip()
    assert {"worried", "frightened"} <= NUDGE_EMOTIONS


def test_frightened_then_reassuring_then_calm_has_landed_cdr_008():
    history = [SpokenTurn("patient", "frightened", "plain"), SpokenTurn("physician", "calm", "reassuring")]
    assert reassurance_landed(history, "patient", "calm") is True
    assert reassurance_landed(history, "patient", "frightened") is False
    worried = [SpokenTurn("patient", "worried", "plain"), SpokenTurn("physician", "calm", "reassuring")]
    assert reassurance_landed(worried, "patient", "frightened") is False  # still afraid: not yet
