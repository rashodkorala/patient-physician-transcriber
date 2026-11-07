"""The interpreter's spoken introduction: who it is, then the names it does not know yet.

Lines are fixed, reviewed text from kb/content/interpreter/, never written by a model. Only reading a
name out of a spoken reply uses the model, and the physician confirms that name before it is used.

@implements MDD-004: Mediator voice: the interpreter speaks as a person between the parties, in reported speech
@implements CDR-003: Participant names and interpreter lines on the visit channel
@see openspec/tdr/cdr/cdr-003-names-and-interpreter-lines.md
"""

import uuid
from pathlib import Path

import yaml
from pydantic import BaseModel

from contracts import InterpreterLine, LinePurpose, LineText, NameRole, clean_name
from llm import Model

LINES_DIR = Path(__file__).parent / "kb" / "content" / "interpreter"


def load_lines(lines_dir: Path = LINES_DIR) -> dict[str, dict[str, str]]:
    """Line templates by language code ("en", "fr", "pa"), then by key."""
    return {p.stem: yaml.safe_load(p.read_text(encoding="utf-8"))["lines"] for p in sorted(lines_dir.glob("*.yaml"))}


LINES = load_lines()


def line_text(language: str, key: str, **names: str) -> str:
    return LINES[language.split("-")[0]][key].format(**names)  # "pa-IN" -> pa.yaml


def interpreter_line(purpose: LinePurpose, texts: list[tuple[str, str]]) -> InterpreterLine:
    return InterpreterLine(
        line_id=f"line-{uuid.uuid4().hex[:10]}",
        purpose=purpose,
        lines=[LineText(language=language, text=text) for language, text in texts],  # type: ignore[arg-type]
    )


def ask_line(
    role: NameRole, physician_language: str, patient_language: str, physician_name: str | None
) -> InterpreterLine:
    """Asks the physician in their language, or the patient in theirs, naming the physician when known."""
    if role == "physician":
        return interpreter_line(
            "ask_physician_name", [(physician_language, line_text(physician_language, "ask_physician_name"))]
        )
    if physician_name:
        text = line_text(patient_language, "ask_patient_name_with_physician", physician=physician_name)
    else:
        text = line_text(patient_language, "ask_patient_name")
    return interpreter_line("ask_patient_name", [(patient_language, text)])


def welcome_line(physician_language: str, patient_language: str, patient_name: str | None) -> InterpreterLine:
    patient_text = (
        line_text(patient_language, "welcome_with_patient", patient=patient_name)
        if patient_name
        else line_text(patient_language, "welcome")
    )
    return interpreter_line(
        "welcome", [(patient_language, patient_text), (physician_language, line_text(physician_language, "welcome"))]
    )


def introduction_line(physician_language: str, patient_language: str) -> InterpreterLine:
    return interpreter_line(
        "introduction",
        [(language, line_text(language, "introduction")) for language in (physician_language, patient_language)],
    )


# ---------- reading a name from a reply ----------


class NameGuess(BaseModel):
    name: str


NAME_SYSTEM = """At the start of a medical visit an interpreter asked someone for the name they want to be called.
Return that name exactly as they gave it, written in Latin script, with no other words.
For the physician, keep a title they used, always writing Doctor as "Dr." ("Dr. Thomas" for "I'm Doctor
Thomas"); never add one.
For the patient, keep the name only, with no title unless they gave one.
If the reply contains no name, return an empty string."""


async def read_name(model: Model, role: NameRole, text: str) -> str | None:
    """The name in a spoken reply, cleaned like a typed one, or None when no usable name was heard."""
    guess = await model.parse(
        purpose="name_extract",
        system=NAME_SYSTEM,
        user=f"<role>{role}</role>\n<reply>{text}</reply>",
        schema=NameGuess,
    )
    try:
        return clean_name(guess.name)
    except ValueError:
        return None
