"""The frozen source set and the shared deterministic checks (ADR-011, CDR-006, CDR-007)."""

import pytest
from chain_records import HEAD, SECRETS, WELCOME, amendment_entry, punjabi_visit, turn_entry

from chains.checks import DraftSource, allowed_tag, check_refs, knows_units, parse_value, values_in
from chains.snapshot import freeze, render_sources
from graph.turn_graph import without_affect_phrase


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


def test_the_affect_phrase_is_left_out_of_every_source_idr_006():
    """IDR-006 review fix 2: the interpreter's affect phrase is its reading, never what the patient said, so the
    frozen sources leave it out of the turn and of a correction, while the chain keeps the text as spoken."""
    worried = "The patient says, sounding worried, that they are scared of the needle."
    corrected = "The patient says, sounding embarrassed, that they missed 2 doses."
    entries = [
        *punjabi_visit(),
        turn_entry("w1", "patient", "pa-IN", "ਮੈਨੂੰ ਸੂਈ ਤੋਂ ਡਰ ਲੱਗਦਾ ਹੈ।", "en-CA", worried),
        amendment_entry("w1", "am-w", "ਮੈਂ 2 ਖੁਰਾਕਾਂ ਛੱਡ ਦਿੱਤੀਆਂ।", corrected),
        turn_entry("w2", "patient", "pa-IN", "ਮੈਨੂੰ ਡਰ ਹੈ।", "en-CA", "The patient says, sounding worried, I am scared."),
    ]
    snapshot = freeze(
        HEAD, entries, [WELCOME], affect_phrases={"am-w": "sounding embarrassed", "w2": "sounding worried"}
    )
    assert snapshot.turn("w1").translation == "The patient says that they missed 2 doses."
    assert snapshot.turn("w2").translation == "The patient says I am scared."
    rendered = render_sources(snapshot.turns)
    assert "sounding" not in rendered
    # Without the phrase recorded, nothing is guessed: the source keeps the text as spoken.
    assert freeze(HEAD, entries).turn("w2").translation.startswith("The patient says, sounding worried")


@pytest.mark.parametrize(
    ("translation", "phrase", "expected"),
    [
        ("The patient says, sounding worried, that it hurts.", "sounding worried", "The patient says that it hurts."),
        (
            "[en-CA] Harpreet says, sounding worried, I am scared.",
            "sounding worried",
            "[en-CA] Harpreet says I am scared.",
        ),
        ("The patient, sounding confused, says it hurts.", "sounding confused", "The patient says it hurts."),
        ("Sounding relieved, the patient says thanks.", "Sounding relieved", "The patient says thanks."),
        ("No phrase here.", "sounding worried", "No phrase here."),
        ("The patient says it hurts.", "", "The patient says it hurts."),
    ],
)
def test_without_affect_phrase_idr_006(translation, phrase, expected):
    assert without_affect_phrase(translation, phrase) == expected
