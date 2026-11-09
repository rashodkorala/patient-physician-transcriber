"""The clinical note: every sentence tagged and sourced, checked by code (CDR-007, ADR-011, ADR-006)."""

import asyncio
from types import SimpleNamespace

import pytest
from chain_records import HEAD, SECRETS, WELCOME, punjabi_visit, run, scripted

from chains.checks import DraftSource, GenerationFailed
from chains.note import HEADINGS, DraftSection, DraftSentence, NoteDraft, generate_note
from chains.snapshot import freeze
from config import RECORD_MODEL
from fake_model import fake_model
from llm import ClaudeModel


def ref(turn_id: str, version: str = "original", kind: str = "turn") -> DraftSource:
    return DraftSource(kind=kind, id=turn_id, version=version)


def note_of(*sentences: DraftSentence, heading: str = "Plan") -> NoteDraft:
    return NoteDraft(sections=[DraftSection(heading=heading, sentences=list(sentences))])


GOOD = DraftSentence(text="Take metformin 500 milligrams twice a day.", tag="physician_stated", sources=[ref("d1")])


def generate(model, entries=None):
    snapshot = freeze(HEAD, entries or punjabi_visit(), [WELCOME])
    return run(generate_note(model, snapshot, note_id="n1", generated_at="2026-11-09T10:10:00+00:00"))


def test_note_every_sentence_tagged_and_sourced_cdr_007():
    stages: list[str] = []

    async def on_stage(stage: str) -> None:
        stages.append(stage)

    snapshot = freeze(HEAD, punjabi_visit(), [WELCOME])
    note = run(generate_note(fake_model(), snapshot, note_id="n1", on_stage=on_stage))
    sentences = [s for section in note.sections for s in section.sentences]
    assert sentences and all(s.tag and s.sources for s in sentences)
    assert all(section.heading in HEADINGS for section in note.sections)
    assert {s.tag for s in sentences} == {"patient_stated", "physician_stated"}
    assert note.based_on_head == HEAD and note.language == "en-CA"
    assert note.untranslated_turn_ids == ("b1", "e1")
    assert note.tag_downgrades == () and note.attempts == 1
    assert [s.sentence_id for s in sentences] == [f"n1-s{i}" for i in range(len(sentences))]
    assert stages == ["generating", "checking"]


def test_stated_tag_downgraded_on_mixed_speakers_cdr_007():
    mixed = DraftSentence(
        text="The patient has diabetes and was given metformin 500 milligrams twice a day.",
        tag="patient_stated",
        sources=[ref("p1"), ref("d1")],
    )
    note = generate(scripted("clinical_note", note_of(mixed, GOOD)))
    first, second = note.sections[0].sentences
    assert first.tag == "ai_inference" and second.tag == "physician_stated"
    assert [(d.sentence_id, d.from_, d.to) for d in note.tag_downgrades] == [
        ("n1-s0", "patient_stated", "ai_inference")
    ]


def test_ai_inference_is_never_upgraded_adr_011():
    inference = DraftSentence(text="The patient is tired.", tag="ai_inference", sources=[ref("p1")])
    note = generate(scripted("clinical_note", note_of(inference)))
    assert note.sections[0].sentences[0].tag == "ai_inference" and note.tag_downgrades == ()


def test_interpreter_line_cited_as_interpreter_stated_adr_011():
    line = DraftSentence(
        text="The interpreter welcomed the patient.",
        tag="interpreter_stated",
        sources=[ref("line-welcome", kind="interpreter_line")],
    )
    note = generate(scripted("clinical_note", note_of(line, heading="History")))
    assert note.sections[0].sentences[0].tag == "interpreter_stated"


@pytest.mark.parametrize(
    "bad",
    [
        DraftSentence(text="Take metformin.", tag="physician_stated", sources=[ref("zz")]),  # unknown id
        DraftSentence(text="Take metformin.", tag="physician_stated", sources=[]),  # no source
        DraftSentence(text="Take metformin.", tag="physician_stated", sources=[ref("d1", "am-9")]),  # wrong version
        DraftSentence(text="Nitroglycerin was discussed.", tag="ai_inference", sources=[ref("b1")]),  # blocked turn
    ],
)
def test_bad_sources_fail_after_one_retry_cdr_007(bad):
    model = scripted("clinical_note", note_of(bad))
    with pytest.raises(GenerationFailed) as failed:
        generate(model)
    assert failed.value.attempts == 2 and len(model.calls) == 2
    retry_prompt = model.calls[1][1]
    assert "<fix_these>" in retry_prompt and failed.value.problems[0] in retry_prompt


def test_number_mismatch_then_retry_succeeds_adr_011():
    wrong = DraftSentence(text="Take metformin 50 milligrams twice a day.", tag="physician_stated", sources=[ref("d1")])
    model = scripted("clinical_note", note_of(wrong), note_of(GOOD))
    note = generate(model)
    assert note.attempts == 2
    assert "50 milligrams" in model.calls[1][1]  # the mismatch was pinned
    assert note.sections[0].sentences[0].text == GOOD.text  # the model's own retry text, never patched


def test_number_mismatch_on_both_attempts_fails_adr_011():
    wrong = DraftSentence(text="Take metformin 500 milligrams once a day.", tag="physician_stated", sources=[ref("d1")])
    with pytest.raises(GenerationFailed) as failed:
        generate(scripted("clinical_note", note_of(wrong)))
    assert "once a day" in failed.value.problems[0]


def test_stated_value_must_be_in_its_own_sources_adr_011():
    # 2 weeks is in the visit, but not in the patient turn this sentence cites.
    misplaced = DraftSentence(text="The patient will return in 2 weeks.", tag="patient_stated", sources=[ref("p1")])
    with pytest.raises(GenerationFailed):
        generate(scripted("clinical_note", note_of(misplaced)))


def test_ai_inference_may_not_introduce_a_dose_adr_011():
    invented = DraftSentence(text="Consider metformin 1000 milligrams later.", tag="ai_inference", sources=[ref("d1")])
    with pytest.raises(GenerationFailed):
        generate(scripted("clinical_note", note_of(invented)))
    supported = DraftSentence(
        text="Metformin 500 milligrams should help fatigue.", tag="ai_inference", sources=[ref("p1"), ref("d1")]
    )
    assert generate(scripted("clinical_note", note_of(supported))).attempts == 1


def test_blocked_and_escalated_turns_never_reach_the_prompt_cdr_007():
    model = fake_model()
    generate(model)
    prompt = model.calls[0][1]
    for secret in SECRETS:
        assert secret not in prompt
    assert '"b1"' not in prompt and '"e1"' not in prompt


def test_note_runs_on_opus_with_high_effort_adr_006():
    calls = {}

    async def parse(**kwargs):
        calls.update(kwargs)
        return SimpleNamespace(stop_reason="end_turn", parsed_output=note_of(GOOD))

    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(parse=parse)))
    snapshot = freeze(HEAD, punjabi_visit())
    asyncio.run(generate_note(ClaudeModel(client=client), snapshot, note_id="n1"))
    assert calls["model"] == RECORD_MODEL == "claude-opus-5-5"
    assert calls["output_config"] == {"effort": "high"} and calls["max_tokens"] == 16000
