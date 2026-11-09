"""Explain-back: code decides critical values, the model only the other instructions (ADR-011, CDR-005)."""

import asyncio
from types import SimpleNamespace

import pytest
from chain_records import HEAD, METFORMIN, SECRETS, punjabi_visit, run, scripted, turn_entry

from chains.checks import GenerationFailed
from chains.explain_back import CodeItemView, DraftItem, ExplainBackDraft, check_explain_back
from chains.snapshot import freeze
from config import LIVE_MODEL
from fake_model import fake_model
from llm import ClaudeModel

PLAN = turn_entry(
    "d1", "physician", "en-CA", "Take metformin 500 milligrams twice a day. Avoid alcohol.", "pa-IN",
    "ਡਾਕਟਰ ਕਹਿ ਰਹੇ ਹਨ ਕਿ ਤੁਸੀਂ ਮੈਟਫਾਰਮਿਨ 500 ਮਿਲੀਗ੍ਰਾਮ ਦਿਨ ਵਿੱਚ ਦੋ ਵਾਰ ਲਓ। ਸ਼ਰਾਬ ਤੋਂ ਬਚੋ।",
    medications=METFORMIN, readback=True,
)  # fmt: skip


def said(turn_id: str, text: str, translation: str, language: str = "pa-IN", settled: str = "final") -> dict:
    return turn_entry(turn_id, "patient", language, text, "en-CA", translation, medications=METFORMIN, settled=settled)


def explain(explanation: list[dict], model=None, plan: list[dict] | None = None):
    plan_snapshot = freeze(HEAD, plan or [PLAN])
    later = freeze("b" * 64, [*(plan or [PLAN]), *explanation])
    ids = [e["entryId"] for e in explanation]
    return run(
        check_explain_back(
            model or fake_model(), explain_back_id="eb1", plan=plan_snapshot, explanation=later.turns_by_id(ids)
        )
    )


def by_kind(result) -> dict:
    return {i.kind: i for i in result.items if i.decided_by == "code"}


def lenient(user: str) -> ExplainBackDraft:
    """A model that calls everything matched, including the frequency the patient never said."""
    from fake_model import _sources

    views = [CodeItemView(item_id=i["itemId"], outcome="matched") for i in _sources(user, "code_items")]
    return ExplainBackDraft(items=[], code_item_views=views)


def test_missed_frequency_flagged_even_when_model_says_matched_cdr_005():
    result = explain(
        [
            said(
                "p1", "ਮੈਂ ਮੈਟਫਾਰਮਿਨ 500 ਮਿਲੀਗ੍ਰਾਮ ਲਵਾਂਗਾ।", "The patient is saying they will take metformin 500 milligrams."
            )
        ],
        scripted("explain_back", lenient),
    )
    items = by_kind(result)
    assert items["frequency"].outcome == "missed"
    assert items["frequency"].decided_by == "code"
    assert items["frequency"].expected == "2 times per day" and items["frequency"].heard is None
    assert items["dose"].outcome == "matched" and items["dose"].evidence_turn_ids == ("p1",)
    assert items["medication"].outcome == "matched"
    assert result.plan_head_hash == HEAD and result.entry_id == "eb1"
    assert result.explanation_turn_ids == ("p1",)


def test_different_frequency_is_contradicted_cdr_005():
    result = explain([said("p1", "ਮੈਟਫਾਰਮਿਨ 500 ਮਿਲੀਗ੍ਰਾਮ ਦਿਨ ਵਿੱਚ ਇੱਕ ਵਾਰ।", "Metformin 500 milligrams once a day.")])
    frequency = by_kind(result)["frequency"]
    assert frequency.outcome == "contradicted"
    assert frequency.heard == "1 times per day" and frequency.evidence_turn_ids == ("p1",)


def test_full_explanation_in_punjabi_matches_every_value_adr_011():
    result = explain(
        [
            said("p1", "ਮੈਂ ਮੈਟਫਾਰਮਿਨ", "Metformin"),
            said("p2", "500 ਮਿਲੀਗ੍ਰਾਮ ਦਿਨ ਵਿੱਚ ਦੋ ਵਾਰ ਲੈਣੀ ਹੈ।", "I take 500 milligrams twice a day."),
        ]
    )
    assert {k: i.outcome for k, i in by_kind(result).items()} == {
        "dose": "matched",
        "frequency": "matched",
        "medication": "matched",
    }


def test_tamil_explanation_with_wrong_dose_is_contradicted_adr_011():
    plan = turn_entry(
        "d1", "physician", "en-CA", "Take metformin 500 milligrams twice a day.", "ta-LK",
        "மருத்துவர் சொல்கிறார்: மெட்ஃபார்மின் 500 மில்லிகிராம் ஒரு நாளைக்கு இரண்டு முறை எடுக்கவும்.",
        medications={"metformin": ["மெட்ஃபார்மின்"]}, readback=True,
    )  # fmt: skip
    explanation = turn_entry(
        "p1", "patient", "ta-LK", "மெட்ஃபார்மின் 50 மில்லிகிராம் ஒரு நாளைக்கு இரண்டு முறை.", "en-CA",
        "Metformin 50 milligrams twice a day.", medications={"metformin": ["மெட்ஃபார்மின்"]},
    )  # fmt: skip
    items = by_kind(explain([explanation], plan=[plan]))
    assert items["dose"].outcome == "contradicted" and items["dose"].heard == "50 mg"
    assert items["frequency"].outcome == "matched"


def test_french_explanation_missing_frequency_cdr_005():
    plan = turn_entry(
        "d1", "physician", "en-CA", "Take 500 milligrams twice a day.", "fr-CA",
        "Le docteur dit de prendre 500 milligrammes deux fois par jour.", readback=True,
    )  # fmt: skip
    explanation = turn_entry("p1", "patient", "fr-CA", "Je prends 500 milligrammes.", "en-CA", "I take 500 milligrams.")
    items = by_kind(explain([explanation], plan=[plan]))
    assert items["frequency"].outcome == "missed" and items["dose"].outcome == "matched"


def test_blocked_and_escalated_turns_are_not_explanation_cdr_005():
    result = explain(
        [
            said("p1", "ਦਿਨ ਵਿੱਚ ਦੋ ਵਾਰ", "twice a day", settled="blocked"),
            said("p2", "ESCALATED-SECRET", "x", settled="escalated"),
            said("p3", "ਮੈਟਫਾਰਮਿਨ 500 ਮਿਲੀਗ੍ਰਾਮ", "Metformin 500 milligrams"),
        ]
    )
    assert result.explanation_turn_ids == ("p3",)
    assert by_kind(result)["frequency"].outcome == "missed"


def test_model_items_kept_with_their_outcome_cdr_005():
    item = DraftItem(
        kind="warning", instruction="Avoid alcohol.", source_turn_ids=["d1"], outcome="missed", evidence_turn_ids=[]
    )
    result = explain(
        [said("p1", "500 ਮਿਲੀਗ੍ਰਾਮ", "500 milligrams")],
        scripted("explain_back", ExplainBackDraft(items=[item], code_item_views=[])),
    )
    model_items = [i for i in result.items if i.decided_by == "model"]
    assert [(i.kind, i.outcome, i.item_id) for i in model_items] == [("warning", "missed", "eb1-m0")]


@pytest.mark.parametrize(
    "bad",
    [
        DraftItem(kind="instruction", instruction="Avoid alcohol.", source_turn_ids=["zz"], outcome="missed", evidence_turn_ids=[]),
        DraftItem(kind="instruction", instruction="Avoid alcohol.", source_turn_ids=[], outcome="missed", evidence_turn_ids=[]),
        DraftItem(kind="instruction", instruction="Take it twice a day.", source_turn_ids=["d1"], outcome="matched", evidence_turn_ids=["p1"]),
        DraftItem(kind="instruction", instruction="Avoid alcohol.", source_turn_ids=["d1"], outcome="matched", evidence_turn_ids=[]),
    ],
)  # fmt: skip
def test_invalid_model_items_retry_once_then_fail_adr_011(bad):
    model = scripted("explain_back", ExplainBackDraft(items=[bad], code_item_views=[]))
    with pytest.raises(GenerationFailed) as failed:
        explain([said("p1", "500 ਮਿਲੀਗ੍ਰਾਮ", "500 milligrams")], model)
    assert failed.value.attempts == 2 and len(model.calls) == 2
    assert "<fix_these>" in model.calls[1][1]


def test_invalid_model_items_then_valid_retry_succeeds_adr_011():
    bad = DraftItem(
        kind="warning", instruction="Avoid alcohol.", source_turn_ids=["zz"], outcome="missed", evidence_turn_ids=[]
    )
    good = bad.model_copy(update={"source_turn_ids": ["d1"]})
    model = scripted(
        "explain_back",
        ExplainBackDraft(items=[bad], code_item_views=[]),
        ExplainBackDraft(items=[good], code_item_views=[]),
    )
    result = explain([said("p1", "500 ਮਿਲੀਗ੍ਰਾਮ", "500 milligrams")], model)
    assert result.attempts == 2


def test_prompt_never_carries_private_or_unspoken_content_adr_011():
    model = fake_model()
    plan = freeze(HEAD, punjabi_visit())
    run(check_explain_back(model, explain_back_id="eb1", plan=plan, explanation=plan.turns_by_id(["p1", "e1"])))
    prompt = model.calls[0][1]
    for secret in SECRETS:
        assert secret not in prompt


def test_explain_back_runs_on_the_live_model_adr_011():
    calls = {}

    async def parse(**kwargs):
        calls.update(kwargs)
        return SimpleNamespace(stop_reason="end_turn", parsed_output=ExplainBackDraft(items=[], code_item_views=[]))

    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(parse=parse)))
    plan = freeze(HEAD, [PLAN])
    asyncio.run(check_explain_back(ClaudeModel(client=client), explain_back_id="eb1", plan=plan, explanation=()))
    assert calls["model"] == LIVE_MODEL == "claude-sonnet-5-5"
    assert calls["output_config"] == {"effort": "low"}
