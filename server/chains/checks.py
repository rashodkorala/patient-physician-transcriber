"""Deterministic checks shared by the explain-back, note, and summary chains (ADR-011 section 2).

Every comparison of a number, dose, frequency, or medication goes through `critical_values.py`, the same code that
checks live turns (CDR-002), so a value reads the same way in a turn, a note, and a summary.

@implements ADR-011: Explain-back, note, and summary: frozen sources, model proposes, code checks provenance and values
@implements CDR-007: Clinical note with provenance and patient summary on the visit channel
@see openspec/tdr/adr/adr-011-grounded-generation-checked-by-code.md
"""

import unicodedata
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field
from rapidfuzz import fuzz

import critical_values
from chains.snapshot import Snapshot, SourceLine, SourceTurn

Tag = Literal["patient_stated", "physician_stated", "companion_stated", "interpreter_stated", "ai_inference"]
AI_INFERENCE: Tag = "ai_inference"
# The speaker every source must have for a stated tag (ADR-011 section 2).
STATED_SPEAKER: dict[str, str] = {
    "patient_stated": "patient",
    "physician_stated": "physician",
    "companion_stated": "companion",
    "interpreter_stated": "interpreter",
}
# Same threshold the live medication check uses (critical_values.check).
MEDICATION_MATCH = 85
MAX_ATTEMPTS = 2  # one retry, then fail or refuse (ADR-011)

Stage = Literal["generating", "checking", "retrying"]
OnStage = Callable[[Stage], Awaitable[None]]


class GenerationFailed(Exception):
    """A generation still failed its checks after one retry, or the model refused twice."""

    def __init__(self, artefact: str, problems: Sequence[str], attempts: int) -> None:
        self.artefact = artefact
        self.problems = list(problems)
        self.attempts = attempts
        super().__init__(f"{artefact} failed after {attempts} attempts: {'; '.join(self.problems)}")


async def report(on_stage: OnStage | None, stage: Stage) -> None:
    if on_stage is not None:
        await on_stage(stage)


# ---------- model-facing source references ----------


class DraftSource(BaseModel):
    """A source the model cites: CDR-007 `SourceRef`."""

    kind: Literal["turn", "interpreter_line"]
    id: str
    version: str = Field(description='"original", or the amendment id the source shows as its version')


@dataclass(frozen=True)
class SourceRef:
    """CDR-007 `SourceRef`, resolved against a snapshot."""

    kind: Literal["turn", "interpreter_line"]
    id: str
    version: str


def resolve(snapshot: Snapshot, ref: DraftSource) -> SourceTurn | SourceLine | None:
    """The frozen source a reference names, only when its kind, id, and version all match."""
    source = snapshot.turn(ref.id) if ref.kind == "turn" else snapshot.line(ref.id)
    if source is None or source.version != ref.version:
        return None
    return source


def speaker_of(source: SourceTurn | SourceLine) -> str:
    return "interpreter" if isinstance(source, SourceLine) else source.speaker


def allowed_tag(tag: Tag, sources: Sequence[SourceTurn | SourceLine]) -> Tag:
    """The tag a sentence may carry: the model's stated tag only when every source has that speaker.

    Code only ever downgrades, to ai_inference; it never upgrades (ADR-011).
    """
    speaker = STATED_SPEAKER.get(tag)
    if speaker is None:
        return AI_INFERENCE
    if sources and all(speaker_of(s) == speaker for s in sources):
        return tag
    return AI_INFERENCE


def check_refs(
    snapshot: Snapshot, label: str, refs: Sequence[DraftSource]
) -> tuple[list[SourceTurn | SourceLine], list[str]]:
    """The resolved sources of one sentence or item, and a problem for each bad or missing reference."""
    problems: list[str] = []
    if not refs:
        problems.append(f"{label} cites no source; cite at least one source turn or interpreter line")
    resolved: list[SourceTurn | SourceLine] = []
    for ref in refs:
        source = resolve(snapshot, ref)
        if source is None:
            problems.append(f"{label} cites {ref.kind} {ref.id!r} version {ref.version!r}, which is not in the sources")
        else:
            resolved.append(source)
    return resolved, problems


# ---------- values ----------


@dataclass(frozen=True)
class Value:
    """One critical value found in a text, normalised for comparison."""

    kind: Literal["dose", "number", "frequency", "medication"]
    key: tuple  # (value, unit) for quantities, (times, period) for frequencies, (name,) for medications
    raw: str
    turn_id: str | None = None

    @property
    def normalised(self) -> str:
        if self.kind == "frequency":
            times, period = self.key
            return f"{times} times per {period}"
        if self.kind == "medication":
            return self.key[0]
        value, unit = self.key
        return f"{value:g} {unit}" if unit else f"{value:g}"

    def same_measure(self, other: "Value") -> bool:
        """Whether two values say the same kind of thing, so a different number between them is a change."""
        if self.kind != other.kind:
            return False
        if self.kind in ("dose", "number"):
            return self.key[1] == other.key[1]
        return True

    def equals(self, other: "Value") -> bool:
        """Same value. A bare number equals a number of any unit, as in the live check (critical_values.check)."""
        if self.kind == "frequency" or other.kind == "frequency":
            return self.kind == other.kind and self.key == other.key
        if self.kind == "medication" or other.kind == "medication":
            return self.kind == other.kind and self.key == other.key
        (value, unit), (other_value, other_unit) = self.key, other.key
        return abs(value - other_value) < 1e-9 and (unit is None or other_unit is None or unit == other_unit)


def knows_units(language: str) -> bool:
    """Whether critical_values.py can read numbers and units in `language` (Sinhala, for one, it cannot)."""
    return critical_values.lang_key(language) in critical_values.UNITS


def medication_names(turns: Iterable[SourceTurn]) -> dict[str, tuple[str, ...]]:
    """Medications named in the sources, each with the forms it was said and spoken in."""
    names: dict[str, list[str]] = {}
    for turn in turns:
        for v in turn.critical_values:
            if v.kind == "medication" and v.source.strip():
                key = v.source.strip().casefold()
                names.setdefault(key, [v.source.strip()])
                if v.translated.strip() and v.translated.strip() not in names[key]:
                    names[key].append(v.translated.strip())
    return {k: tuple(v) for k, v in names.items()}


def counted_forms(medications: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    """First words of every medication name, so "one aspirin" reads as a count (critical_values._counted_forms)."""
    firsts = {unicodedata.normalize("NFC", n).split()[0].casefold() for forms in medications.values() for n in forms}
    return tuple(f for f in firsts if len(f) >= 3)


def names_medication(text: str, forms: Sequence[str]) -> bool:
    said = unicodedata.normalize("NFC", text).casefold()
    for form in forms:
        name = unicodedata.normalize("NFC", form).casefold()
        if name and (name in said or fuzz.partial_ratio(name, said) >= MEDICATION_MATCH):
            return True
    return False


def values_in(
    text: str,
    language: str,
    medications: dict[str, tuple[str, ...]] | None = None,
    turn_id: str | None = None,
) -> list[Value]:
    """Every quantity, frequency, and known medication in `text`, read as the live check reads them."""
    medications = medications or {}
    found: list[Value] = []
    for q in critical_values.quantities(text, language, counted_forms(medications)):
        kind = "dose" if q.unit in critical_values.DOSE_UNITS else "number"
        found.append(Value(kind=kind, key=(q.value, q.unit), raw=q.raw, turn_id=turn_id))
    for norm, raw in critical_values.frequencies(text, language):
        found.append(Value(kind="frequency", key=norm, raw=raw, turn_id=turn_id))
    for key, forms in medications.items():
        if names_medication(text, forms):
            found.append(Value(kind="medication", key=(key,), raw=forms[0], turn_id=turn_id))
    return found


def source_values(
    source: SourceTurn | SourceLine, medications: dict[str, tuple[str, ...]] | None = None
) -> list[Value]:
    """Values in a source, as said and as spoken, in every language it was heard in."""
    if isinstance(source, SourceLine):
        return [v for lang, text in source.texts for v in values_in(text, lang, medications, source.line_id)]
    return [
        *values_in(source.source_text, source.source_language, medications, source.turn_id),
        *values_in(source.translation, source.target_language, medications, source.turn_id),
    ]


def parse_value(kind: str, raw: str, language: str) -> Value | None:
    """A CDR-002 critical value's raw text ("500 milligrams", "twice a day") read as one normalised value."""
    if kind == "frequency":
        found = critical_values.frequencies(raw, language)
        return Value(kind="frequency", key=found[0][0], raw=raw) if found else None
    if kind in ("dose", "number"):
        quantities = critical_values.quantities(raw, language)
        if not quantities:
            return None
        q = quantities[0]
        return Value(kind="dose" if q.unit in critical_values.DOSE_UNITS else "number", key=(q.value, q.unit), raw=raw)
    if kind == "medication" and raw.strip():
        return Value(kind="medication", key=(raw.strip().casefold(),), raw=raw.strip())
    return None
