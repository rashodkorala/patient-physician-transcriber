"""The interpreter's introduction lines and name reading (mediator-voice tasks 2.4 to 2.6, CDR-003)."""

import asyncio

import pytest

from introduction import LINES, NameGuess, ask_line, introduction_line, read_name, welcome_line
from llm import ScriptedModel


def test_every_language_has_every_line():
    keys = {frozenset(lines) for lines in LINES.values()}
    assert len(keys) == 1 and set(LINES) == {"en", "fr", "pa", "si", "ta"}


@pytest.mark.parametrize("language", ["en", "fr", "pa", "si", "ta"])
def test_lines_use_only_known_placeholders(language):
    for key, text in LINES[language].items():
        # Fails on any placeholder the flow does not fill.
        text.format(physician="Dr. Thomas", patient="Harpreet")
        assert ("{physician}" in text) == key.endswith("with_physician")
        assert ("{patient}" in text) == key.endswith("with_patient")


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
