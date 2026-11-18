"""The clinical note and patient summary never guess gender from a name (affect-in-words task 9.5, MDD-004).

From the live run of 16 November 2026: the note called the patient "she" throughout, though no gender was given and
every relay said "they" (`docs/voice-test.md`, "Affect in words run, 16 November 2026").
"""

import asyncio

import pytest
from chain_records import HEAD, WELCOME, punjabi_visit, scripted, turn_entry

from chains.checks import DraftSource, GenerationFailed
from chains.note import SYSTEM as NOTE_SYSTEM
from chains.note import DraftSection, DraftSentence, NoteDraft, generate_note
from chains.snapshot import freeze
from chains.summary import SYSTEM as SUMMARY_SYSTEM
from fake_model import field


def _note(text: str, tag: str = "patient_stated") -> NoteDraft:
    sentence = DraftSentence(text=text, tag=tag, sources=[DraftSource(kind="turn", id="p1", version="original")])
    return NoteDraft(sections=[DraftSection(heading="History", sentences=[sentence])])


def _generate(m, entries=None):
    snapshot = freeze(HEAD, entries or punjabi_visit(), [WELCOME])
    return asyncio.run(generate_note(m, snapshot, note_id="n1", generated_at="2026-11-16T10:00:00+00:00"))


def test_note_that_guesses_the_patients_gender_is_retried_then_refused_mdd_004():
    """The live note called the patient "she" throughout, though every source said "they"."""
    m = scripted("clinical_note", _note("She has diabetes and feels very tired."), _note("They have diabetes."))
    note = _generate(m)
    assert note.attempts == 2
    retry = [user for purpose, user in m.calls if purpose == "clinical_note"][1]
    assert 'says "she", but no source it cites gives that gender' in field(retry, "fix_these")
    with pytest.raises(GenerationFailed) as failed:
        _generate(scripted("clinical_note", _note("She has diabetes and feels very tired.")))
    assert any('says "she"' in p for p in failed.value.problems)
    assert "Never guess anyone's gender from their name." in " ".join(NOTE_SYSTEM.split())


def test_note_keeps_a_gender_its_source_states_mdd_004():
    entries = [
        turn_entry(
            "p1", "patient", "pa-IN", "ਮੇਰੀ ਮਾਂ ਨੂੰ ਸ਼ੂਗਰ ਹੈ।", "en-CA", "The patient is saying their mother has diabetes; she is 70."
        )
    ]  # fmt: skip
    note = _generate(scripted("clinical_note", _note("The patient's mother has diabetes; she is 70.")), entries)
    assert note.attempts == 1
    titled = [turn_entry("p1", "patient", "pa-IN", "ਮੈਂ ਤੁਰਦਾ ਹਾਂ।", "en-CA", "Mr Singh is saying they walk.")]
    assert _generate(scripted("clinical_note", _note("He walks.")), titled).attempts == 1


def test_summary_is_told_never_to_guess_gender_mdd_004():
    summary = " ".join(SUMMARY_SYSTEM.split())
    assert "Never guess anyone's gender from their name." in summary
    assert "use their name, their role, or a respectful form that avoids it" in summary
