"""The patient summary: values as the patient heard them, confirmed doses present, or refused (CDR-007, ADR-011)."""

import asyncio
from types import SimpleNamespace

from chain_records import HEAD, SECRETS, WELCOME, punjabi_visit, run, scripted, turn_entry

from chains.checks import DraftSource
from chains.snapshot import freeze
from chains.summary import DraftSummarySentence, SummaryDraft, generate_summary
from config import RECORD_MODEL
from fake_model import fake_model
from llm import ClaudeModel, ModelRefused

DOSE = "ਮੈਟਫਾਰਮਿਨ 500 ਮਿਲੀਗ੍ਰਾਮ ਦਿਨ ਵਿੱਚ ਦੋ ਵਾਰ ਲਓ।"
RETURN = "2 ਹਫ਼ਤਿਆਂ ਬਾਅਦ ਵਾਪਸ ਆਓ।"


def summary_of(*texts: str, sources: tuple[str, ...] = ("d1",)) -> SummaryDraft:
    refs = [DraftSource(kind="turn", id=i, version="original") for i in sources]
    return SummaryDraft(sentences=[DraftSummarySentence(text=t, sources=refs) for t in texts])


def summarise(model, entries=None, language="pa-IN"):
    snapshot = freeze(HEAD, entries or punjabi_visit(), [WELCOME])
    return run(generate_summary(model, snapshot, summary_id="sum1", language=language))


def test_faithful_punjabi_summary_passes_cdr_007():
    outcome = summarise(fake_model())
    summary = outcome.summary
    assert summary is not None and not outcome.refused
    assert summary.language == "pa-IN" and summary.based_on_head == HEAD and summary.check == "passed"
    assert [s.sentence_id for s in summary.sentences] == [f"sum1.{i}" for i in range(len(summary.sentences))]
    assert {(v.kind, v.source_turn_id) for v in summary.values} >= {("dose", "d1"), ("frequency", "d1")}
    assert [(c.attempt, c.outcome) for c in outcome.checks] == [(1, "passed")]


def test_wrong_dose_refused_after_one_retry_cdr_007():
    model = scripted("patient_summary", summary_of("ਮੈਟਫਾਰਮਿਨ 50 ਮਿਲੀਗ੍ਰਾਮ ਦਿਨ ਵਿੱਚ ਦੋ ਵਾਰ ਲਓ।", RETURN))
    outcome = summarise(model)
    assert outcome.refused and outcome.summary is None
    assert [(c.attempt, c.outcome) for c in outcome.checks] == [(1, "failed"), (2, "failed")]
    problems = {(m.problem, m.found, m.source_turn_id) for m in outcome.checks[-1].mismatches}
    assert ("changed", "50 ਮਿਲੀਗ੍ਰਾਮ", "d1") in problems
    assert ("missing", None, "d1") in {(m.problem, m.found, m.source_turn_id) for m in outcome.checks[-1].mismatches}
    assert "500 ਮਿਲੀਗ੍ਰਾਮ" in model.calls[1][1]  # the expected value was pinned in the retry
    assert outcome.detail


def test_wrong_dose_then_correct_retry_passes_adr_011():
    model = scripted("patient_summary", summary_of("ਮੈਟਫਾਰਮਿਨ 50 ਮਿਲੀਗ੍ਰਾਮ ਦਿਨ ਵਿੱਚ ਦੋ ਵਾਰ ਲਓ।"), summary_of(DOSE, RETURN))
    outcome = summarise(model)
    assert outcome.summary is not None
    assert [c.outcome for c in outcome.checks] == ["failed", "passed"]


def test_missing_confirmed_dose_refused_cdr_007():
    outcome = summarise(scripted("patient_summary", summary_of(RETURN, sources=("d2",))))
    assert outcome.refused
    missing = [m for m in outcome.checks[-1].mismatches if m.problem == "missing"]
    assert {(m.kind, m.expected) for m in missing} == {("dose", "500 ਮਿਲੀਗ੍ਰਾਮ"), ("frequency", "ਦਿਨ ਵਿੱਚ ਦੋ ਵਾਰ")}


def test_missing_confirmed_frequency_refused_cdr_007():
    outcome = summarise(scripted("patient_summary", summary_of("ਮੈਟਫਾਰਮਿਨ 500 ਮਿਲੀਗ੍ਰਾਮ ਲਓ।")))
    assert outcome.refused
    assert [(m.kind, m.problem) for m in outcome.checks[-1].mismatches] == [("frequency", "missing")]


def test_number_nobody_said_is_unsupported_adr_011():
    outcome = summarise(scripted("patient_summary", summary_of(DOSE, "3 ਦਿਨਾਂ ਵਿੱਚ ਫ਼ੋਨ ਕਰੋ।")))
    assert outcome.refused
    assert [(m.problem, m.found) for m in outcome.checks[-1].mismatches] == [("unsupported", "3 ਦਿਨਾਂ")]


def test_unsourced_or_unknown_source_sentence_refused_adr_011():
    outcome = summarise(scripted("patient_summary", summary_of(DOSE, sources=())))
    assert outcome.refused and outcome.checks[-1].problems
    outcome = summarise(scripted("patient_summary", summary_of(DOSE, sources=("b1",))))
    assert outcome.refused


def test_unknown_unit_language_refused_without_a_model_call_adr_011():
    model = fake_model()
    entries = [
        turn_entry("d1", "physician", "en-CA", "Take 500 milligrams twice a day.", "si-LK", "මිලිග්‍රෑම් 500", readback=True)
    ]
    outcome = summarise(model, entries, language="si-LK")
    assert outcome.refused and outcome.checks == () and "si-LK" in outcome.detail
    assert model.calls == []


def test_tamil_and_french_summaries_checked_in_their_own_words_adr_011():
    tamil = turn_entry(
        "d1", "physician", "en-CA", "Take metformin 500 milligrams twice a day.", "ta-LK",
        "மருத்துவர் சொல்கிறார்: மெட்ஃபார்மின் 500 மில்லிகிராம் ஒரு நாளைக்கு இரண்டு முறை எடுக்கவும்.",
        medications={"metformin": ["மெட்ஃபார்மின்"]}, readback=True,
    )  # fmt: skip
    assert summarise(fake_model(), [tamil], "ta-LK").summary is not None
    wrong = summary_of("மெட்ஃபார்மின் 500 மில்லிகிராம் ஒரு நாளைக்கு மூன்று முறை எடுக்கவும்.")
    outcome = summarise(scripted("patient_summary", wrong), [tamil], "ta-LK")
    assert outcome.refused
    assert ("frequency", "changed") in {(m.kind, m.problem) for m in outcome.checks[-1].mismatches}

    french = turn_entry(
        "d1", "physician", "en-CA", "Take 500 milligrams twice a day.", "fr-CA",
        "Le docteur dit de prendre 500 milligrammes deux fois par jour.", readback=True,
    )  # fmt: skip
    assert summarise(fake_model(), [french], "fr-CA").summary is not None
    outcome = summarise(
        scripted("patient_summary", summary_of("Prenez 5 milligrammes deux fois par jour.")), [french], "fr-CA"
    )
    assert outcome.refused


def test_model_refusal_twice_refuses_the_summary_adr_011():
    def refuse(_user: str):
        raise ModelRefused("patient_summary: stop_reason=refusal")

    outcome = summarise(scripted("patient_summary", refuse))
    assert outcome.refused and [c.outcome for c in outcome.checks] == ["failed", "failed"]


def test_blocked_and_escalated_turns_never_reach_the_prompt_cdr_007():
    model = fake_model()
    summarise(model)
    prompt = model.calls[0][1]
    for secret in SECRETS:
        assert secret not in prompt
    assert "4 ਮਿਲੀਗ੍ਰਾਮ" not in prompt


def test_summary_runs_on_opus_adr_006():
    calls = {}

    async def parse(**kwargs):
        calls.update(kwargs)
        return SimpleNamespace(stop_reason="end_turn", parsed_output=summary_of(DOSE))

    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(parse=parse)))
    snapshot = freeze(HEAD, punjabi_visit())
    outcome = asyncio.run(generate_summary(ClaudeModel(client=client), snapshot, summary_id="s", language="pa-IN"))
    assert outcome.summary is not None
    assert calls["model"] == RECORD_MODEL == "claude-opus-5-5"
