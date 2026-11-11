"""The interpreter's own fixed words: the consent notice, its introduction and the names it does not know yet, the
patient's signals relayed to the physician, and the closing check.

Lines are fixed, reviewed text from kb/content/interpreter/ and kb/content/consent/, never written by a model.
Only reading a name out of a spoken reply uses the model, and the physician confirms that name before it is
used. The introduction starts only after consent (CDR-005); the server enforces that order.

@implements MDD-004: Mediator voice: the interpreter speaks as a person between the parties, in reported speech
@implements MDD-005: Trust across the barrier
@implements CDR-003: Participant names and interpreter lines on the visit channel
@implements CDR-005: Consent and explain-back on the visit channel
@implements CDR-008: Patient signals, manner, trust updates, companion turns, and the closing check on the visit channel
@see openspec/tdr/cdr/cdr-003-names-and-interpreter-lines.md
@see openspec/tdr/cdr/cdr-005-consent-and-explain-back-events.md
@see openspec/tdr/cdr/cdr-008-patient-voice-manner-and-trust-events.md
"""

import hashlib
import uuid
from pathlib import Path

import yaml
from pydantic import BaseModel

from contracts import ConsentNotice, InterpreterLine, LinePurpose, LineText, NameRole, PatientSignal, clean_name
from hash_chain import canonical_json
from llm import Model

LINES_DIR = Path(__file__).parent / "kb" / "content" / "interpreter"
CONSENT_DIR = Path(__file__).parent / "kb" / "content" / "consent"
ENGLISH = "en-CA"


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


# ---------- the patient's signals and the closing check (CDR-008) ----------

# The signals the interpreter relays aloud; `repeat` is a replay and says nothing new.
SIGNAL_LINE_KEYS: dict[str, LinePurpose] = {"not_understood": "signal_not_understood", "slower": "signal_slower"}


def named_line(language: str, key: str, patient_name: str | None) -> str:
    """A line naming the patient when the name is known, else its `_unnamed` form ("the patient")."""
    if patient_name:
        return line_text(language, key, patient=patient_name)
    return line_text(language, f"{key}_unnamed")


def signal_line(signal: PatientSignal, physician_language: str, patient_name: str | None) -> InterpreterLine:
    """What the interpreter says to the physician, in the physician's language, when the patient signals."""
    key = SIGNAL_LINE_KEYS[signal]
    return interpreter_line(key, [(physician_language, named_line(physician_language, key, patient_name))])


def ask_if_clear_line(physician_language: str, patient_language: str, patient_name: str | None) -> InterpreterLine:
    """The closing check: asked of the patient in their language (spoken), shown to the physician in theirs."""
    return interpreter_line(
        "ask_if_clear",
        [
            (language, named_line(language, "ask_if_clear", patient_name))
            for language in (patient_language, physician_language)
        ],
    )


# ---------- the consent notice (CDR-005) ----------


def load_consent_notices(consent_dir: Path = CONSENT_DIR) -> dict[str, ConsentNotice]:
    """One reviewed notice per patient language, with the English it is shown beside, by patient language.

    `noticeId` is `{language}-v{version}`, so it changes whenever the text does. A patient-language file names
    the English version it was written against; a mismatch fails at start-up rather than showing a pair that
    was never reviewed together.
    """
    files = {p.stem: yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted(consent_dir.glob("*.yaml"))}
    english = files.pop(ENGLISH)
    notices: dict[str, ConsentNotice] = {}
    for language, data in files.items():
        if data["language"] != language:
            raise ValueError(f"{language}.yaml says it is {data['language']}")
        if str(data["english_version"]) != str(english["version"]):
            raise ValueError(f"{language}.yaml was written against English v{data['english_version']}")
        version = str(data["version"])
        notice_id = f"{language}-v{version}"
        notices[language] = ConsentNotice(
            notice_id=notice_id,
            speech_id=f"consent-{notice_id}",
            version=version,
            language=language,  # type: ignore[arg-type]
            lines=[
                LineText(language=language, text=" ".join(data["text"].split())),  # type: ignore[arg-type]
                LineText(language=ENGLISH, text=" ".join(english["text"].split())),
            ],
        )
    return notices


CONSENT_NOTICES = load_consent_notices()


def notice_sha256(notice: ConsentNotice) -> str:
    """SHA-256 of the notice exactly as shown, both lines, stored in every consent chain entry (CDR-006)."""
    return hashlib.sha256(canonical_json([line.wire() for line in notice.lines])).hexdigest()


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
