"""One frozen source set for every grounded generation (ADR-011 section 1).

A snapshot is built from CDR-006 record chain payloads alone (`RecordEntry`: `{entryId, kind, at, body}`), plus the
interpreter's own lines (CDR-003), which are not chain entries. It holds:

- the chain head hash the generation is based on (`basedOnHead`, `planHeadHash`);
- every turn that settled as spoken (`final`, which includes read-back confirmed turns), at its effective version:
  the latest applied amendment, else the original (CDR-006);
- the interpreter's own lines, citable only as `interpreter_stated`;
- the ids of blocked, unclear, and escalated turns, as gaps, without any text.

A patient or companion turn's affect phrase ("sounding worried", IDR-006) is taken out of its translation here,
using the phrase the turn graph recorded: it is the interpreter's reading of how the speaker sounded, so no
generation may restate it as something the speaker said.

Only the fields named here are copied out of an entry, so nothing private can reach a model even if an entry
carried it: no emotion, certainty, back-translation, confidence, nudge, injection or tamper state, and no
unspoken translation. Consent, confirmation, explain-back, interpreter, and summary entries are never sources.

@implements ADR-011: Explain-back, note, and summary: frozen sources, model proposes, code checks provenance and values
@implements CDR-006: Record chain entries, review corrections, and tamper control
@implements IDR-006: Affect phrase in the reporting frame, and one constant voice delivery
@see openspec/tdr/adr/adr-011-grounded-generation-checked-by-code.md
"""

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from contracts import InterpreterLine
from graph.turn_graph import without_affect_phrase

SourceKind = Literal["turn", "interpreter_line"]
ORIGINAL = "original"


@dataclass(frozen=True)
class SourceValue:
    """A public critical value of a turn (CDR-002 `CaptionCriticalValue`): as said, and as spoken to the listener."""

    kind: str
    source: str
    translated: str


@dataclass(frozen=True)
class SourceTurn:
    """A turn that was spoken, at its effective version."""

    turn_id: str
    version: str  # "original" or the applied amendmentId (CDR-006)
    speaker: str  # patient, physician, or companion
    speaker_name: str | None
    source_language: str
    source_text: str
    target_language: str
    translation: str
    critical_values: tuple[SourceValue, ...] = ()
    readback_confirmed: bool = False

    def text_in(self, language: str) -> str | None:
        """This turn's words in `language`, as said or as spoken to the listener, or None."""
        if self.source_language == language:
            return self.source_text
        if self.target_language == language:
            return self.translation
        return None


@dataclass(frozen=True)
class SourceLine:
    """Something the interpreter said itself (CDR-003), in each language it was spoken in."""

    line_id: str
    purpose: str
    texts: tuple[tuple[str, str], ...]  # (language, text)

    version: str = ORIGINAL

    def text_in(self, language: str) -> str | None:
        return next((text for lang, text in self.texts if lang == language), None)


@dataclass(frozen=True)
class Snapshot:
    """The frozen sources one generation may read and cite."""

    head_hash: str
    turns: tuple[SourceTurn, ...] = ()
    interpreter_lines: tuple[SourceLine, ...] = ()
    untranslated_turn_ids: tuple[str, ...] = ()
    _turns_by_id: dict[str, SourceTurn] = field(init=False, repr=False, compare=False)
    _lines_by_id: dict[str, SourceLine] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_turns_by_id", {t.turn_id: t for t in self.turns})
        object.__setattr__(self, "_lines_by_id", {line.line_id: line for line in self.interpreter_lines})

    def turn(self, turn_id: str) -> SourceTurn | None:
        return self._turns_by_id.get(turn_id)

    def line(self, line_id: str) -> SourceLine | None:
        return self._lines_by_id.get(line_id)

    def turns_by_id(self, turn_ids: Iterable[str]) -> tuple[SourceTurn, ...]:
        """The spoken turns among `turn_ids`, in the order given; ids that are not sources are skipped."""
        return tuple(t for t in (self.turn(i) for i in turn_ids) if t is not None)


def _values(raw: Iterable[Mapping[str, Any]] | None) -> tuple[SourceValue, ...]:
    return tuple(
        SourceValue(
            kind=str(v.get("kind", "")), source=str(v.get("source", "")), translated=str(v.get("translated", ""))
        )
        for v in raw or ()
    )


def _speaker_name(body: Mapping[str, Any], speaker: str) -> str | None:
    if speaker == "physician":
        return body.get("physicianName")
    if speaker == "patient":
        return body.get("patientName")
    return None


def freeze(
    head_hash: str,
    entries: Sequence[Mapping[str, Any]],
    interpreter_lines: Iterable[InterpreterLine] = (),
    affect_phrases: Mapping[str, str] | None = None,
) -> Snapshot:
    """The snapshot of a record chain, taken when a generation starts.

    `entries` are the CDR-006 `RecordEntry` payloads oldest first, as stored in the chain (for example
    `[e.payload for e in chain.entries]`), and `head_hash` is the chain head at that moment. `affect_phrases` maps
    a turn or amendment id to the affect phrase in its translation, which the source leaves out (IDR-006).
    """
    phrases = affect_phrases or {}
    originals: dict[str, SourceTurn] = {}
    order: list[str] = []
    gaps: list[str] = []
    for entry in entries:
        kind, body = entry.get("kind"), entry.get("body") or {}
        if kind == "turn":
            turn_id = str(body.get("turnId") or entry.get("entryId"))
            settled = body.get("settledAs") or body.get("status")
            if settled != "final" or body.get("translation") is None:
                # ADR-003: an unclear turn is never spoken, so it is a gap like a blocked one.
                if settled in ("blocked", "escalated", "unclear"):
                    gaps.append(turn_id)
                continue
            speaker = str(body.get("speaker"))
            originals[turn_id] = SourceTurn(
                turn_id=turn_id,
                version=ORIGINAL,
                speaker=speaker,
                speaker_name=_speaker_name(body, speaker),
                source_language=str(body.get("sourceLanguage")),
                source_text=str(body.get("sourceText", "")),
                target_language=str(body.get("targetLanguage")),
                translation=without_affect_phrase(str(body.get("translation")), phrases.get(turn_id, "")),
                critical_values=_values(body.get("criticalValues")),
                readback_confirmed=bool(body.get("readbackConfirmed", False)),
            )
            order.append(turn_id)
        elif kind == "amendment":
            # Only applied corrections are chained (CDR-006), and only of spoken turns.
            segment_id = str(body.get("segmentId"))
            current = originals.get(segment_id)
            if current is None:
                continue
            version = str(body.get("amendmentId") or entry.get("entryId"))
            originals[segment_id] = SourceTurn(
                turn_id=segment_id,
                version=version,
                speaker=current.speaker,
                speaker_name=current.speaker_name,
                source_language=current.source_language,
                source_text=str(body.get("sourceText", "")),
                target_language=current.target_language,
                translation=without_affect_phrase(str(body.get("translation", "")), phrases.get(version, "")),
                critical_values=_values(body.get("criticalValues")),
                readback_confirmed=current.readback_confirmed,
            )
    lines = tuple(
        SourceLine(line_id=line.line_id, purpose=line.purpose, texts=tuple((t.language, t.text) for t in line.lines))
        for line in interpreter_lines
    )
    return Snapshot(
        head_hash=head_hash,
        turns=tuple(originals[i] for i in order),
        interpreter_lines=lines,
        untranslated_turn_ids=tuple(dict.fromkeys(gaps)),
    )


def source_record(source: SourceTurn | SourceLine) -> dict[str, Any]:
    """What a model is shown of one source: ids, speaker, and the words as said and as spoken. Nothing else."""
    if isinstance(source, SourceLine):
        return {
            "kind": "interpreter_line",
            "id": source.line_id,
            "version": source.version,
            "speaker": "interpreter",
            "lines": [{"language": lang, "text": text} for lang, text in source.texts],
        }
    return {
        "kind": "turn",
        "id": source.turn_id,
        "version": source.version,
        "speaker": source.speaker,
        "speakerName": source.speaker_name,
        "sourceLanguage": source.source_language,
        "sourceText": source.source_text,
        "targetLanguage": source.target_language,
        "spokenTranslation": source.translation,
    }


def render_sources(sources: Iterable[SourceTurn | SourceLine]) -> str:
    """Sources as JSON for a prompt, one record per source, in order."""
    return json.dumps([source_record(s) for s in sources], ensure_ascii=False, indent=1)
