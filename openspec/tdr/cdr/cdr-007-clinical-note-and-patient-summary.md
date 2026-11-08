---
id: cdr-007
title: "Clinical note with provenance and patient summary on the visit channel"
status: proposed
date: 2026-11-08
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: api-contract
related_decisions: [mdd-001, mdd-003, adr-006, adr-007, adr-011, cdr-001, cdr-002, cdr-003, cdr-004, cdr-005, cdr-006, idr-003]
related_specs: [demo-consultation-flow]
related_changes: [demo-night-mvp]
ai_context:
  implementation_priorities:
    - "Additive to CDR-001: new commands and events and new optional visit.state fields"
    - "The note is controller only; the summary is public, but only after its deterministic value check passes"
    - "Every note sentence has exactly one provenance tag and at least one source link, checked by code (ADR-011)"
    - "A summary is spoken only sentence by sentence through the speak gate, so CDR-004's 60 second ceiling holds"
  framework_hints:
    - "Pydantic models in server/contracts.py; TypeScript in web/lib/contracts.ts; regenerate web/lib/generated/"
    - "Add note.generate and summary.generate to CONTROLLER_COMMANDS; add note.status, note.ready, and summary.check to CONTROLLER_ONLY_EVENTS"
    - "Extend the speakable() gate in server/main.py with summary sentence ids; CDR-004 voice.started reuses it"
  validation_rules:
    - "note.ready and visit.state.note never reach screen or review connections"
    - "A note or summary is built only from the frozen sources defined in ADR-011: settled spoken turns at their effective version"
    - "A summary whose value check fails after one retry is refused: never published publicly, never spoken"
    - "GET /api/speech/{id} serves a summary sentence only for the current, passed summary, in the patient's language"
    - "A note or summary made from an older chain head is marked stale, never silently updated"
affects: [server/contracts.py, server/main.py, server/visit_store.py, web/lib/contracts.ts, web/lib/generated/, web/components/Controller.tsx, web/components/SharedScreen.tsx]
implementation_refs: []
test_refs: []
---

# CDR-007: Clinical note with provenance and patient summary on the visit channel

> Contract Decision Record. Only a human may set `status: accepted`.

## Summary

Adds the commands, events, schemas, and speak gate extension for the post-visit artefacts of beat 8 (MDD-003): the English clinical note where every sentence carries one provenance tag and links to its source turns (task 3.6), and the plain-language summary in the patient's language, read aloud, with a deterministic dose check that refuses a mismatched dose (task 3.7).
How the content is generated and checked is ADR-011; this record fixes the messages and who receives what.
Additive to CDR-001, CDR-003, and CDR-004.

## Context

- **Integration point**: server chains (ADR-004 single-pass chains on the models chosen by ADR-006) to the controller, the shared screen, and the review screen.
- **Related decisions**: CDR-001 and CDR-002 define no note or summary messages.
  CDR-003's speak gate serves only turns and interpreter lines; CDR-004 accepts `voice.started` only for ids the gate allows and clears any speech after 60 seconds.
  CDR-006 defines the chain whose head each artefact cites.
- **Requirements**: every note sentence has exactly one tag (patient-stated, physician-stated, companion-stated, interpreter-stated, or AI inference) and a link to its sources; selecting a sentence highlights its source turn with the original and its translation; the summary is in the patient's language, spoken on request, and every dose and number is identical to the transcript.
- **Constraints**: the physician remains the final author of the record (MDD-001), so the note is a draft for the physician; only the controller browser plays audio (CDR-004).

## Decision

1. **Generation is a controller command, results are snapshots.**
   `note.generate` and `summary.generate` freeze the sources (ADR-011) and the chain head, and the result names that head as `basedOnHead`.
   Regenerating replaces the current artefact; when the chain grows after generation, the artefact is marked stale.
2. **The note is private to the physician.**
   `note.ready` and the note in `visit.state` go to controller connections only.
   Click-to-source needs no new message: each sentence's sources name turns and versions the controller already holds.
3. **The summary is public only once checked.**
   A summary that passes ADR-011's value check is published to every role in `summary.ready`; one that fails after one retry is refused, and only the controller sees why.
4. **Read aloud by sentence.**
   Each summary sentence has its own speech id, served by the speak gate only for the current, passed summary.
   The review screen or the controller asks for it with `summary.read_aloud`; the controller plays the sentences in order and reports each one with CDR-004 `voice.started` and `voice.ended`.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| HTTP endpoints `POST /api/note` and `POST /api/summary` | Familiar request and response | A second path that bypasses the visit channel's role filter; screens would poll for the summary | Everything else lives on the channel; one role filter |
| Note on every screen | Patient sees the note too | The note is an unsigned draft that may hold AI inference; MDD-001 makes the physician its author | Physician first; the patient verifies the transcript and gets the summary |
| Free-text note with footnote markers | Natural reading | Tags and links cannot be checked per sentence | Structured sentences, so code can check every tag and link |
| Summary spoken as one speech id | One request | A summary can exceed CDR-004's 60 second ceiling, so the orb would drop to silent mid-speech | Per-sentence ids keep the ceiling and let playback stop cleanly |
| Summary from the note | Consistent with the note | Errors compound; the note holds English inference the patient did not hear | Both are made from the same frozen turns (ADR-011) |
| Summary shown even when the check fails, with a warning | Patient gets something | A wrong dose in the patient's hands is the harm this product exists to prevent | Refused; the physician can regenerate |

## Contract Specification

### Commands (client to server)

| Command | Sender | Server rule |
|---|---|---|
| `note.generate` | Controller | Refused unless at least one turn settled as spoken, no read-back is pending, no correction is in flight, no explain-back is `checking`, and no note is being generated |
| `summary.generate` | Controller | Same rules as `note.generate`, and no summary is being generated |
| `summary.read_aloud` (`summaryId`) | Review or controller; a screen's copy is dropped | Accepted only for the current summary with `check: "passed"`. Publishes `summary.speak` to controllers |
| `summary.stop` (`summaryId`) | Review or controller; a screen's copy is dropped | Publishes `summary.speak` with `action: "stop"` to controllers |

### Events (server to clients)

| Event | Who receives it | When |
|---|---|---|
| `note.status` (`ArtefactStatus`) | *Controller only* | `generating`, `checking`, `retrying`, `ready`, or `failed` |
| `note.ready` (`ClinicalNote`) | *Controller only* | A note passed ADR-011's checks |
| `summary.status` (`ArtefactStatus`) | Every role, with `detail` omitted for screen and review | `generating`, `checking`, `retrying`, `ready`, or `refused` |
| `summary.check` (`SummaryCheck`) | *Controller only* | Every check outcome, passed or failed, with the values compared |
| `summary.ready` (`PatientSummary`) | Every role | A summary passed the value check |
| `summary.speak` (`SummarySpeak`) | *Controller only* | The patient or physician asked to play or stop the summary |
| `artefacts.stale` (`ArtefactsStale`) | Every role | The chain grew after the current note or summary was made |

### `visit.state` additions (all optional)

- Controller only: `note: ClinicalNote | null`, `noteStale: boolean`, `summaryChecks: SummaryCheck[]`.
- Every role: `summary: PatientSummary | null` (only a passed summary is ever held here), `summaryStale: boolean`.

### Speak gate extension (CDR-003, CDR-004)

- `GET /api/speech/{id}` also serves `{summaryId}.{n}`, the `n`th sentence (from 0) of the current passed summary, in the summary's language.
  A refused, replaced, or unknown summary id, and any language other than the summary's, return 404.
- CDR-004 rule 2 applies unchanged: `voice.started` is accepted for a summary sentence id because the gate allows it.
- Summary text is spoken with the interpreter-line delivery (calm, neutral), never with tone derived from a turn's emotion.

### Stale rule

When a chain entry is appended after an artefact's `basedOnHead`, the server sets its stale flag and publishes `artefacts.stale`.
A stale summary can still be read and played, with a stale notice on every screen; the physician regenerates to refresh.
Nothing is updated silently.

## Data Schemas

- `ArtefactStatus`: `{ artefactId: string, kind: "note" | "summary", stage: "generating" | "checking" | "retrying" | "ready" | "failed" | "refused", detail?: string }`.
  `detail` is controller only.
- `SourceRef`: `{ kind: "turn" | "interpreter_line", id: string, version: "original" | amendmentId }`.
  `version` is the effective version frozen at generation (CDR-006); interpreter line refs use `version: "original"`.
- `NoteSentence`: `{ sentenceId: string, text: string, tag: "patient_stated" | "physician_stated" | "companion_stated" | "interpreter_stated" | "ai_inference", sources: SourceRef[] }`, with at least one source.
- `ClinicalNote`: `{ noteId: string, language: "en-CA", basedOnHead: string, generatedAt: ISO-8601 string, sections: { heading: "Presenting complaint" | "History" | "Assessment" | "Plan" | "Follow-up", sentences: NoteSentence[] }[], untranslatedTurnIds: string[], tagDowngrades: { sentenceId: string, from: string, to: "ai_inference" }[] }`.
  `untranslatedTurnIds` lists blocked and escalated turns the note could not use, so the physician sees the gap.
  `tagDowngrades` lists sentences whose model tag code changed to `ai_inference` (ADR-011).
- `SummarySentence`: `{ sentenceId: string, index: integer, text: string, sources: SourceRef[] }`.
- `PatientSummary`: `{ summaryId: string, language: PatientLanguage, basedOnHead: string, generatedAt: ISO-8601 string, sentences: SummarySentence[], values: { kind: CriticalKind, text: string, sourceTurnId: string }[], check: "passed" }`.
- `SummaryCheck` (controller only): `{ summaryId: string, attempt: 1 | 2, outcome: "passed" | "failed", mismatches: { kind: CriticalKind, expected: string, found: string | null, sourceTurnId: string | null, problem: "changed" | "missing" | "unsupported" }[] }`.
- `SummaryRef` (command payload of `summary.read_aloud` and `summary.stop`): `{ summaryId: string }`.
- `SummarySpeak`: `{ summaryId: string, action: "play" | "stop", speechIds: string[] }`.
- `ArtefactsStale`: `{ note: boolean, summary: boolean, headHash: string }`; for screen and review, `note` is always `false`.

## Evolution Strategy

Additive to CDR-001, CDR-003, and CDR-004: new messages and optional `visit.state` fields; the speak gate serves one more id form.
Physician editing and signing of the note, and export to an EHR, are later additive commands (`note.edit`, `note.sign`) that append to the chain without changing these shapes.
New note section headings and provenance tags need a superseding CDR, because screens render them by value.

## Testing Requirements

Contract tests in pytest and `npm run check:contracts` cover every new message, schema, and `visit.state` field.
Tests named for this record (for example `test_note_every_sentence_tagged_cdr_007`) cover, with the mocked model (EDR-002):
- every `NoteSentence` has exactly one tag and at least one source that resolves to a frozen source turn and version; a fixture note with a sentence missing sources fails after one retry and is never published;
- a sentence tagged `patient_stated` whose sources include a physician turn is published as `ai_inference` and listed in `tagDowngrades`;
- `note.ready` and `visit.state.note` never reach screen or review connections;
- a summary whose dose differs from the confirmed dose on both attempts is refused: no `summary.ready`, no public text, `summary.status` `refused` on every role, and `GET /api/speech/{summaryId}.0` returns 404;
- a summary that omits a read-back-confirmed dose is refused with `problem: "missing"`;
- a passed summary is published to every role, and each sentence id is served by the speak gate in the patient's language only; `voice.started` for a sentence id is accepted;
- `summary.read_aloud` from a screen connection is dropped, and from review publishes `summary.speak` to controllers only;
- appending a chain entry after generation publishes `artefacts.stale` and sets the stale flags;
- blocked and escalated turns are never sources and appear in `untranslatedTurnIds`;
- a corrected turn is cited at its amendment version.
A front-end test checks that selecting a note sentence highlights its source turn with the original and translation, and that the shared screen shows a passed summary in the patient's language and a refusal notice in both languages otherwise.

## Consequences

- **Positive**: every note sentence is traceable or honestly marked as inference; a wrong dose never reaches the patient's summary or ears; playback fits the existing speaking state.
- **Negative**: more messages; the summary can be refused on stage if the model drifts, which needs a fallback in rehearsal.
- **Risks and mitigations**: a refused summary on stage; mitigated by one automatic retry with the expected values pinned (ADR-011), the physician's regenerate action, and replay mode (TDM-001).

## Implementation

Code governed by this record carries `@contract ws:/ws/visit` (and `@contract GET /api/speech/{id}` for the gate) and `@implements CDR-007: Clinical note with provenance and patient summary on the visit channel`.
Demo-night-mvp tasks 3.6 and 3.7 build it, after this record and ADR-011 are accepted.

Open questions for the decision owner:
1. Should the note also appear in a separate record view (`/record` in the design), and if so, which connection role does that view use? As drafted, only controller connections receive it.
2. Should an accepted summary be appended to the chain as part of the record given to the patient, rather than pointing at the head, as drafted?
3. Should a summary omitting a confirmed dose be refused (as drafted) or published with the omission flagged to the physician?

## Review Notes

- 2026-11-08, Claude (agent): Drafted as a proposal for the supervising session, for demo-night-mvp tasks 3.6 and 3.7. Awaiting human review; do not implement until accepted.
