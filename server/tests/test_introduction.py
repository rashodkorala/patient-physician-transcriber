"""The interpreter's introduction lines and name reading (mediator-voice tasks 2.4 to 2.6, CDR-003), and the signal
and closing-check lines (CDR-008)."""

import asyncio

import pytest

from introduction import (
    LINES,
    NameGuess,
    ask_if_clear_line,
    ask_line,
    introduction_line,
    read_name,
    signal_line,
    welcome_line,
)
from llm import ScriptedModel

LANGUAGES = ["en", "fr", "pa", "si", "ta"]
# Lines that name the patient: the welcome, and the CDR-008 lines whose `_unnamed` twin stands in without a name.
NAMED_PATIENT_KEYS = {"welcome_with_patient", "signal_not_understood", "signal_slower", "ask_if_clear"}


def test_every_language_has_every_line():
    keys = {frozenset(lines) for lines in LINES.values()}
    assert len(keys) == 1 and set(LINES) == set(LANGUAGES)


@pytest.mark.parametrize("language", LANGUAGES)
def test_lines_use_only_known_placeholders(language):
    for key, text in LINES[language].items():
        # Fails on any placeholder the flow does not fill.
        text.format(physician="Dr. Thomas", patient="Harpreet")
        assert ("{physician}" in text) == key.endswith("with_physician")
        assert ("{patient}" in text) == (key in NAMED_PATIENT_KEYS), key
        if key in NAMED_PATIENT_KEYS - {"welcome_with_patient"}:
            assert "{" not in LINES[language][f"{key}_unnamed"]


# ---------- the patient's signals and the closing check (CDR-008) ----------

CODES = {"en": "en-CA", "fr": "fr-CA", "pa": "pa-IN", "si": "si-LK", "ta": "ta-LK"}


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("signal", ["not_understood", "slower"])
def test_signal_line_names_the_patient_in_every_language_cdr_008(language, signal):
    code = CODES[language]
    named = signal_line(signal, code, "Mr Singh")
    unnamed = signal_line(signal, code, None)
    assert named.purpose == unnamed.purpose == f"signal_{signal}"
    assert [line.language for line in named.lines] == [code]  # the physician's language only
    assert "Mr Singh" in named.lines[0].text and "{" not in named.lines[0].text
    assert "Mr Singh" not in unnamed.lines[0].text and "{" not in unnamed.lines[0].text
    assert named.lines[0].text != unnamed.lines[0].text


def test_signal_line_in_english_relays_the_signal_cdr_008():
    assert signal_line("slower", "en-CA", "Mr Singh").lines[0].text == "Mr Singh is asking you to speak more slowly."
    assert signal_line("not_understood", "en-CA", None).lines[0].text == (
        "The patient is saying they did not understand that. Could you say it another way?"
    )


@pytest.mark.parametrize("language", ["fr", "pa", "si", "ta"])
def test_ask_if_clear_is_patient_language_first_then_physician_cdr_008(language):
    code = CODES[language]
    line = ask_if_clear_line("en-CA", code, "Harpreet")
    assert line.purpose == "ask_if_clear"
    assert [part.language for part in line.lines] == [code, "en-CA"]
    assert all("Harpreet" in part.text and "{" not in part.text for part in line.lines)
    unnamed = ask_if_clear_line("en-CA", code, None)
    assert unnamed.lines[1].text == "Is there anything the doctor said today that you would like explained again?"
    assert all("Harpreet" not in part.text for part in unnamed.lines)


def test_introduction_is_in_both_languages_and_asks_name_the_physician():
    intro = introduction_line("en-CA", "fr-CA")
    assert [line.language for line in intro.lines] == ["en-CA", "fr-CA"]
    ask = ask_line("patient", "en-CA", "fr-CA", "Dr. Thomas")
    assert ask.lines[0].language == "fr-CA" and ask.lines[0].text.startswith("Dr. Thomas est votre médecin")
    assert ask_line("physician", "en-CA", "fr-CA", None).lines[0].language == "en-CA"
    welcome = welcome_line("en-CA", "pa-IN", "Harpreet")
    assert "Harpreet" in welcome.lines[0].text and "Harpreet" not in welcome.lines[1].text


def reply_model(name: str) -> ScriptedModel:
    return ScriptedModel({"name_extract": lambda user: NameGuess(name=name)})


@pytest.mark.parametrize(
    ("guess", "expected"),
    [("  Dr.  Thomas ", "Dr. Thomas"), ("", None), ("Room 4", None), ("x" * 61, None)],
)
def test_read_name_cleans_like_a_typed_name(guess, expected):
    assert asyncio.run(read_name(reply_model(guess), "physician", "...")) == expected
