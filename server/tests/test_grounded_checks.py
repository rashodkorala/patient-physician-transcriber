"""The frozen source set and the shared deterministic checks (ADR-011, CDR-006, CDR-007)."""

import pytest
from chain_records import HEAD, SECRETS, WELCOME, amendment_entry, punjabi_visit

from chains.checks import DraftSource, allowed_tag, check_refs, knows_units, parse_value, values_in
from chains.snapshot import freeze, render_sources


def test_snapshot_holds_only_spoken_turns_and_lists_gaps_adr_011():
    snapshot = freeze(HEAD, punjabi_visit(), [WELCOME])
    assert snapshot.head_hash == HEAD
    assert [t.turn_id for t in snapshot.turns] == ["p1", "d1", "d2"]
    assert snapshot.untranslated_turn_ids == ("b1", "e1")
    assert [line.line_id for line in snapshot.interpreter_lines] == ["line-welcome"]
    assert snapshot.turn("d1").readback_confirmed and snapshot.turn("d1").speaker_name == "Thomas"


def test_prompt_sources_carry_no_private_or_unspoken_content_adr_011():
    rendered = render_sources([*freeze(HEAD, punjabi_visit(), [WELCOME]).turns])
    for secret in SECRETS:
        assert secret not in rendered
    for name in ("emotion", "certainty", "backTranslation", "confidence", "toneLabel"):
        assert name not in rendered


def test_corrected_turn_is_its_amendment_version_cdr_006():
    entries = [
        *punjabi_visit(),
        amendment_entry("p1", "am-1", "ਮੈਨੂੰ ਸ਼ੂਗਰ ਹੈ।", "The patient is saying they have diabetes."),
    ]
    turn = freeze(HEAD, entries).turn("p1")
    assert turn.version == "am-1"
    assert turn.source_text == "ਮੈਨੂੰ ਸ਼ੂਗਰ ਹੈ।"
    # The original version is no longer a citable source.
    _, problems = check_refs(freeze(HEAD, entries), "s", [DraftSource(kind="turn", id="p1", version="original")])
    assert problems


def test_amendment_of_a_blocked_turn_never_makes_it_a_source_adr_011():
    entries = [*punjabi_visit(), amendment_entry("b1", "am-2", "Take 0.4 milligrams.", "0.4 ਮਿਲੀਗ੍ਰਾਮ")]
    assert freeze(HEAD, entries).turn("b1") is None


@pytest.mark.parametrize(
    ("tag", "speakers", "allowed"),
    [
        ("patient_stated", ["p1"], "patient_stated"),
        ("patient_stated", ["p1", "d1"], "ai_inference"),
        ("physician_stated", ["p1"], "ai_inference"),
        ("companion_stated", ["p1"], "ai_inference"),
        ("interpreter_stated", ["line-welcome"], "interpreter_stated"),
        ("interpreter_stated", ["line-welcome", "d1"], "ai_inference"),
        ("ai_inference", ["p1"], "ai_inference"),  # never upgraded
    ],
)
def test_stated_tag_needs_every_source_by_that_speaker_adr_011(tag, speakers, allowed):
    snapshot = freeze(HEAD, punjabi_visit(), [WELCOME])
    sources = [snapshot.turn(i) or snapshot.line(i) for i in speakers]
    assert allowed_tag(tag, sources) == allowed


def test_unknown_id_and_missing_source_are_problems_adr_011():
    snapshot = freeze(HEAD, punjabi_visit())
    _, unknown = check_refs(snapshot, "s", [DraftSource(kind="turn", id="zz", version="original")])
    _, blocked = check_refs(snapshot, "s", [DraftSource(kind="turn", id="b1", version="original")])
    _, none = check_refs(snapshot, "s", [])
    assert unknown and blocked and none


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("ਮੈਟਫਾਰਮਿਨ 500 ਮਿਲੀਗ੍ਰਾਮ ਦਿਨ ਵਿੱਚ ਦੋ ਵਾਰ ਲਓ।", "pa-IN"),
        ("ਪੰਜ ਸੌ ਮਿਲੀਗ੍ਰਾਮ ਦਿਨ ਵਿਚ ਦੋ ਵਾਰ", "pa-IN"),
        ("மெட்ஃபார்மின் 500 மில்லிகிராம் ஒரு நாளைக்கு இரண்டு முறை எடுக்கவும்.", "ta-LK"),
        ("Prenez 500 milligrammes de metformine deux fois par jour.", "fr-CA"),
    ],
)
def test_values_read_in_gurmukhi_tamil_and_french_adr_011(text, language):
    found = {(v.kind, v.key) for v in values_in(text, language)}
    assert ("dose", (500.0, "mg")) in found
    assert ("frequency", (2, "day")) in found


def test_value_parsing_and_unit_languages_adr_011():
    assert parse_value("dose", "500 milligrams", "en-CA").normalised == "500 mg"
    assert parse_value("frequency", "twice a day", "en-CA").normalised == "2 times per day"
    assert parse_value("medication", "Metformin", "en-CA").normalised == "metformin"
    assert knows_units("pa-IN") and knows_units("ta-LK") and knows_units("fr-CA")
    assert not knows_units("si-LK")
