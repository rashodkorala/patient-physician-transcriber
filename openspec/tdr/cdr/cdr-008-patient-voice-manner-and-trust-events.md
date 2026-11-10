---
id: cdr-008
title: "Patient signals, manner, trust updates, companion turns, and the closing check on the visit channel"
status: accepted
date: 2026-11-10
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: api-contract
related_decisions: [mdd-005, adr-001, adr-003, adr-007, cdr-001, cdr-002, cdr-003, cdr-006, idr-003, idr-005]
related_specs: [patient-voice, manner-in-relay, trust-signals-for-the-physician, companion-turns]
related_changes: [trust-across-the-barrier]
ai_context:
  implementation_priorities:
    - "Every addition is additive to CDR-001, CDR-002, CDR-003, and CDR-006; no existing field changes shape"
    - "patient.signal is accepted from the review role only; trust.update is controller only; everything else goes to every role"
    - "A patient signal is chained as a record entry of kind signal"
  framework_hints:
    - "Pydantic models in server/contracts.py; mirrored types in web/lib/contracts.ts; fixtures in server/tests/fixtures/ generated into web/lib/generated/"
    - "Interpreter lines for signals and the closing check are fixed text in server/kb/content/interpreter/*.yaml, never model-written"
  validation_rules:
    - "TurnCaption.manner is set only for a final physician turn; null for every patient or companion turn and for blocked or escalated turns"
    - "trust.update, and visit.state.trust, never reach a screen or review connection, live or in a snapshot"
    - "A patient.signal from a controller is refused with error; from a screen it is dropped"
    - "The same device may not send two signals within two seconds; the second is refused with command.refused busy"
affects: [server/contracts.py, server/main.py, server/visit_store.py, web/lib/contracts.ts]
implementation_refs: []
test_refs: []
---

# CDR-008: Patient signals, manner, trust updates, companion turns, and the closing check on the visit channel

> Contract Decision Record. Every boundary between the screens and the server has one. Only a human may set `status: accepted`.

## Summary

Adds to the visit channel the patient's own signals, the manner of each turn, the physician-only trust updates, companion turns, and the interpreter's closing check, as decided in MDD-005 and IDR-005.
Produced by the server; consumed by the controller, the shared screen, and the patient's device (the review role).

## Context

- **Integration point**: `ws://<server>/ws/visit` (CDR-001), the `TurnResult` and `TurnCaption` shapes (CDR-002), interpreter lines (CDR-003), and the record chain (CDR-006).
- **Related decisions**: MDD-005, IDR-005, ADR-003 (the interpreter request the patient can make is the existing `interpreter.request`), ADR-007 (in-memory state), IDR-003 (hash chain).
- **Requirements**: `patient-voice`, `manner-in-relay`, `trust-signals-for-the-physician`, `companion-turns`.

## Decision

Adopt the additions below as version 1 of this contract.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| A new `patient` role | Clear naming | Every role filter, test, and snapshot would change; the review role already is the patient's device | Keep `review`; the route is `/patient` |
| Signals as free text | Flexible | Untranslatable; cannot be a fixed interpreter line | Three fixed signals, plus the existing pause and interpreter request |
| Trust updates for every role | Simpler filtering | Leaks the patient's emotion to the room | Controller only, like `turn.analysis` |

## Contract Specification

New types:

- `Manner = "plain" | "warm" | "reassuring" | "gentle" | "serious" | "urgent" | "apologetic" | "encouraging"` (IDR-005).
- `PatientSignal = "not_understood" | "slower" | "repeat"`.
- `TrustCueKind = "reassurance" | "understanding" | "culture"`.
- `LinePurpose` (CDR-003) gains `signal_not_understood`, `signal_slower`, and `ask_if_clear`.
- `EntryKind` (CDR-006) gains `signal`.

Changes to existing shapes (all additive):

- `TurnResult` gains `manner: Manner` (every turn, read from the words; controller only as before).
- `TurnCaption` gains `manner: Manner | null`: the result's manner for a `final` physician turn, otherwise `null`.
  `TurnEntryBody` inherits it, so a chained physician turn records its manner.
- `TurnSubmit.speaker` may be `companion`; the language must then be the patient's language.
  `turn.started`, `turn.result`, the chain entry, the note's `companion_stated` tag, and every screen's speaker label already carry `companion`.
- `visit.state` for every role gains `signals: PatientSignalEntry[]`, oldest first.
  `visit.state` for the controller also gains `trust: TrustUpdate[]`, oldest first.

| Command (client to server) | Sender | Rules |
|---|---|---|
| `patient.signal` (`signal`) | Review (the patient's device) only | Refused with `command.refused` `invalid` before consent, while paused, and for `repeat` when no translation has yet been spoken in the patient's language; refused `busy` within two seconds of the same device's previous signal. A controller copy is refused with `error`; a screen copy is dropped |
| `visit.ask_if_clear` | Controller only | Refused with `error` before consent, while paused, and while a read-back is pending |
| `turn.submit` with `speaker: "companion"` | Controller | As a patient turn, labelled companion; never produces an empathy nudge |

| Event (server to clients) | When |
|---|---|
| `patient.signal` (`PatientSignalEntry`) | Every role, as soon as a signal is accepted; the shared screen shows it in both languages for a few seconds, the controller lists it |
| `interpreter.line` with purpose `signal_not_understood` or `signal_slower` | Every role, right after the signal; one line in the physician's language, spoken through the speak gate by the controller: "Mr Singh is saying they did not understand that. Could you say it another way?" |
| `interpreter.line` with purpose `ask_if_clear` | Every role; two lines, the patient's language first (spoken) and the physician's language (shown) |
| `trust.update` (`TrustUpdate`) | *Controller only.* Once per settled `final` turn, after the trust advisor returns (or at once with `cue: null` if it fails), and once per accepted patient signal |
| `record.integrity` | After the `signal` chain entry, as after every append (CDR-006) |

`repeat` causes no server speech: the controller replays the last spoken translation in the patient's language through `GET /api/speech/{turnId}?language=` (CDR-003), which already allows a spoken turn to be fetched again.

## Data Schemas

```json
PatientSignalEntry: { "signalId": "string", "signal": "not_understood | slower | repeat", "afterTurnId": "string | null", "at": "ISO-8601" }
TrustCue: { "kind": "reassurance | understanding | culture", "text": "string, English, at most 200 characters" }
TrustUpdate: {
  "turnId": "string | null",
  "speaker": "patient | physician | companion | null",
  "emotion": "Emotion | null",
  "manner": "Manner | null",
  "reassuranceLanded": "boolean | null",
  "signal": "PatientSignal | null",
  "cue": "TrustCue | null",
  "at": "ISO-8601"
}
```

- `afterTurnId` is the most recent settled turn when the signal arrived, or `null` before the first.
- For a turn update: `turnId`, `speaker`, and `manner` are set; `emotion` is set for patient and companion turns and `null` for physician turns; `signal` is `null`.
- `reassuranceLanded` is set only on a patient turn that follows (a) an earlier patient turn whose emotion was `worried`, `embarrassed`, `in_pain`, or `confused` and (b) a physician turn between them whose manner was `reassuring`, `warm`, `gentle`, or `encouraging`: `true` when this turn's emotion is `calm` or `relieved`, otherwise `false`; `null` in every other case.
- For a signal update: `signal`, `turnId` (the `afterTurnId`), and `cue` of kind `understanding` are set; `speaker`, `emotion`, `manner`, and `reassuranceLanded` are `null`.
- The `signal` chain entry body is the `PatientSignalEntry`; its `entryId` is the `signalId`.
- Nothing in `TrustUpdate` is ever written into the note, the summary, or the record chain.

## Evolution Strategy

Additive fields are non-breaking.
Before first implementation the record may be amended in place with a dated review note; afterwards enum changes or removals need a superseding CDR.

## Testing Requirements

- Pydantic and TypeScript fixture tests for `PatientSignalEntry`, `TrustUpdate`, a `TurnCaption` with `manner`, and `visit.state` for both roles.
- Channel tests: a signal from the review role reaches controller, screen, and review as `patient.signal` and is chained; the interpreter line follows in the physician's language only; a controller copy gets `error`; a screen copy produces nothing; a second signal within two seconds gets `busy`; `repeat` before any spoken translation gets `invalid`; signals are refused before consent and while paused.
- `trust.update` never reaches a screen or review connection, live or in `visit.state`; a worried patient turn, a reassuring physician turn, then a calm patient turn yields `reassuranceLanded: true`; a worried one yields `false`; a calm turn with no preceding worry yields `null`.
- A companion turn is accepted in the patient's language, refused in the physician's language, relayed with the companion frame, labelled companion in the caption and the chain, and produces no nudge.
- `visit.ask_if_clear` produces one interpreter line with two languages, speakable only in the patient's language; refused before consent, while paused, and during a read-back.
- No `TurnCaption` for a patient or companion turn ever carries a non-null `manner`.

## Consequences

- **Positive**: one additive contract; every screen can be built against fixtures offline.
- **Negative**: the controller must hold the trust timeline; the chain gains a new kind every verifier must know.
- **Risks and mitigations**: a signal burst, held by the two second rule; a replay request for a turn the speak gate no longer allows, which the browser treats as a 404 and shows nothing.

## Implementation

Code carries `@implements CDR-008: Patient signals, manner, trust updates, companion turns, and the closing check` and `@contract ws:/ws/visit`.

## Review Notes

- 2026-11-10, Claude (agent): Drafted alongside MDD-005 and IDR-005.
- 2026-11-10, rashodkorala: Blanket authorisation given in session (see MDD-005). Recorded as accepted by Claude (agent) at rashodkorala's explicit request; rashodkorala reviews the built result.
