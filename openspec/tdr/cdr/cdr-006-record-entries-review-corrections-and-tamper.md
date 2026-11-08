---
id: cdr-006
title: "Record chain entries, transcript review corrections, and the tamper control"
status: proposed
date: 2026-11-08
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: api-contract
related_decisions: [mdd-001, mdd-003, adr-004, adr-007, cdr-001, cdr-002, cdr-003, cdr-004, cdr-005, idr-003, tdm-002]
related_specs: [demo-consultation-flow]
related_changes: [demo-night-mvp]
ai_context:
  implementation_priorities:
    - "The record is append-only: a correction or confirmation is a new chain entry; the original turn entry is never edited"
    - "Every chain entry has an entryId; record.integrity.brokenAt is the entryId of the first entry that fails verification"
    - "A re-spoken correction goes through the same turn graph and the same blocked and escalated rules as a live turn"
    - "The tamper control is presenter-only and visible on shared screens only as record.integrity turning broken"
  framework_hints:
    - "Pydantic models in server/contracts.py; TypeScript in web/lib/contracts.ts; regenerate web/lib/generated/"
    - "server/hash_chain.py (IDR-003) keeps {index, payload, prevHash, hash}; this record fixes what payload holds"
    - "Add segment.confirm and segment.amend to a REVIEW_COMMANDS set; add demo.tamper_record to CONTROLLER_COMMANDS behind the presenter gate"
    - "Add segment.analysis and demo.tamper_state to CONTROLLER_ONLY_EVENTS"
  validation_rules:
    - "Only settled turns, consent changes, confirmations, applied corrections, and explain-back results are chained"
    - "A chain entry payload never holds emotion, certainty, back-translation, confidence, empathy nudges, or an unspoken translation"
    - "segment.amend is accepted only from a review connection, only for a settled final patient turn, only in the visit's patient language"
    - "A correction that ends blocked or escalated is refused and never chained; the current version stays"
    - "segment.confirm names the version it confirms and is refused if that version is no longer current"
    - "demo.tamper_record is refused outside presenter mode and from any non-controller connection"
    - "demo.tamper_state never reaches screen or review connections, live or via visit.state"
affects: [server/contracts.py, server/main.py, server/visit_store.py, server/hash_chain.py, web/lib/contracts.ts, web/lib/generated/]
implementation_refs: []
test_refs: []
---

# CDR-006: Record chain entries, transcript review corrections, and the tamper control

> Contract Decision Record. Only a human may set `status: accepted`.

## Summary

Fixes what the append-only record chain (IDR-003) contains and how a chain failure is named on the channel, defines the payloads of CDR-001's `segment.confirm` and `segment.amend` so the patient can confirm or correct their own turns by re-speaking while every original is kept (task 3.5), and adds the presenter-only `demo.tamper_record` command for the tamper demonstration (task 3.8).
Additive to CDR-001.

## Context

- **Integration point**: the visit store and hash chain on the server, the review screen (patient's phone), the controller, and the shared screen.
- **Related decisions**:
  - IDR-003 keeps entries `{index, payload, prevHash, hash}` and reports the first broken index, while CDR-001's `record.integrity.brokenAt` is a `segmentId`; nothing maps one to the other, and nothing says whether amendments are chained.
  - CDR-001 lists `segment.confirm` and `segment.amend` (review screen) and the event `segment.amended` (`segmentId`, `by`, `action`, `newText?`), but defines no command payloads, no re-speak path, no refusal, and no history.
  - IDR-003 decides "a hidden demo control alters one stored segment to show detection", but no channel command carries it; CDR-001 only has the TDM-002 injection commands.
- **Requirements**: the patient corrects a turn by re-speaking it, and the turn then shows the correction and its translation while the original stays visible in its history; the record verified badge turns broken and names the altered turn when a past turn is changed outside the review process.
- **Constraints**: review and screen connections receive only public data (CDR-001, CDR-002); `error` is controller only, so refusals to the review screen use `command.refused` (CDR-005).

## Decision

1. **One chain, typed entries, named by id.**
   Every chain entry's payload is a `RecordEntry` with a unique `entryId` and a `kind`.
   For a turn, `entryId` is the `turnId`, so CDR-001's `segmentId` and `turnId` are the same value.
   `record.integrity.brokenAt` carries the `entryId` of the first entry that fails verification, which for a turn is its `segmentId`.
2. **Amendments are chained, and so are confirmations.**
   An applied correction is a new `amendment` entry pointing at the turn entry; a confirmation is a new `confirmation` entry.
   The original `turn` entry is never edited, so the original stays in the record and in every history view.
3. **Corrections are re-interpreted, not typed.**
   `segment.amend` carries the recognised text of the patient re-speaking the turn; the server runs it through the turn graph (ADR-004) and applies it only if it ends `final`.
4. **The tamper control is presenter-only.**
   `demo.tamper_record` alters one stored entry's payload in place, without rehashing, so verification fails at that entry; the shared screens learn of it only through `record.integrity`.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Edit the turn in place and keep a history list beside it | Simple reads | Breaks the hash chain on every correction; the badge would turn red for a legitimate correction | IDR-003 is append-only |
| `brokenAt` as the numeric chain index | Matches IDR-003 output directly | Screens would need the index to entry mapping; breaks CDR-001's `segmentId` type | `entryId` keeps CDR-001's meaning for turns and extends it to other entries |
| Chain only turns, keep amendments outside the chain | Smaller chain | A correction could be altered without detection, which is the very thing the badge claims to show | Amendments are part of the record |
| Typed corrections from the review screen | No speech needed on the phone | Typed text skips the patient's own language input mode and the beat says re-speak; still needs translation and checks | Re-speak per the spec; typing can be added later as another source |
| Corrections applied without the turn graph (translate only) | Faster | A correction could change a dose with no critical value check | Same safety rules as a live turn |
| Tamper by deleting an entry | Also detected | The badge must name the altered turn; deletion names the next entry | Altering the payload names the altered turn itself |
| Tamper control as a server-start flag | No command | Cannot be triggered on stage at the right moment | Command, behind TDM-002's presenter gate |

## Contract Specification

### Record chain entries

The chain holds, in order of occurrence, one entry for each:

| `kind` | Appended when | `entryId` |
|---|---|---|
| `turn` | A turn settles: spoken `final`, read-back confirmed, `blocked`, or `escalated` | The `turnId` (equal to the CDR-001 `segmentId`) |
| `consent` | `consent.give` or `consent.withdraw` is accepted (CDR-005) | A new id |
| `amendment` | A correction is applied | The `amendmentId` |
| `confirmation` | `segment.confirm` is accepted | A new id |
| `explain_back` | An explain-back check finishes (CDR-005) | The `explainBackId` |
| `interpreter_request` | `interpreter.request` or `visit.mark_high_risk` is recorded (CDR-001; ADR-003 requires escalations in the transcript) | A new id |

Never chained: rejected or discarded turns, turns captured during a pause (none are captured), turns discarded by consent withdrawal, refused corrections, empathy nudges, `turn.analysis` content, and demo injection or tamper state.
Generated notes and summaries are not chained; they point at the chain head they were made from (CDR-007).

`record.integrity` is published to every role after every append and after verification fails.
`brokenAt` is the `entryId` of the first entry whose recomputed hash or `prevHash` link does not match; when that entry is a turn, it is the turn's `segmentId`, so screens can highlight the turn.

### Commands (client to server)

| Command | Sender | Server rule |
|---|---|---|
| `segment.confirm` (`segmentId`, `version`) | Review; a controller or screen copy is refused | Accepted only for a settled `final` patient turn when `version` is the current version (`"original"` or the latest `amendmentId`) and it is not already confirmed. Appends a `confirmation` entry |
| `segment.amend` (`segmentId`, `text`, `language`, `recognitionConfidence`) | Review; a controller or screen copy is refused | Accepted only for a settled `final` patient turn, with `language` equal to the visit's patient language, non-empty `text`, and no other correction in flight for any turn. Runs the turn graph on `text` |
| `demo.tamper_record` (`entryId`) | Controller in presenter mode only (TDM-002 gate); refused from any other connection | Accepted only for an existing `turn` or `amendment` entry, at most once per visit. Alters the stored payload's text in place without rehashing, then runs verification |

The patient corrects only patient turns in this version; physician corrections are out of scope (see open questions).

### Correction flow

1. The review screen recognises the patient re-speaking in the patient's language (ADR-005) and sends `segment.amend`.
2. The server publishes `segment.status` stages (`translating`, `verifying`, `retrying`) to every role, without text.
3. The turn graph result decides:
   - `final`: the server appends an `amendment` entry, publishes `segment.analysis` (full CDR-002 `TurnResult`) to controllers and `segment.amended` to every role, then `segment.status` `applied`.
   - `blocked` or `escalated`: nothing is chained, the current version stays, the controller receives `segment.analysis`, and every role receives `segment.status` `refused` with `reason` `blocked` or `escalated` and no translation.
     The patient is asked to re-speak.
   - `readback_required` never occurs, because only physician turns need read-back.
4. A confirmation of an earlier version stops being current when a correction is applied; the history shows both.
5. A correction's translation is shown, not spoken, in this version; the speak gate (CDR-003) does not serve amendment ids.

### Events (server to clients)

| Event | Who receives it | When |
|---|---|---|
| `segment.status` (`SegmentStatus`) | Every role | Each stage of a correction, and its outcome |
| `segment.analysis` (`SegmentAnalysis`) | *Controller only* | A correction's full turn graph result |
| `segment.amended` (CDR-001, extended) | Every role | A correction was applied or a confirmation recorded |
| `demo.tamper_state` (`TamperState`) | *Controller only, presenter mode* | The tamper control altered an entry |
| `record.integrity` (CDR-001) | Every role | After every append and after verification fails |

### `visit.state` additions (all optional)

- Every role: `segments: SegmentHistory[]`, one per turn that has a confirmation or a correction.
- Controller only: `tamper: TamperState | null`, and in `SegmentHistory.amendments[]` the full `analysis: TurnResult`.
- The existing `turns` keep the original `TurnCaption` or `TurnResult` unchanged; the effective version of a turn is its latest applied amendment, else the original.

### Record view marking

The controller and the record view mark a tampered entry as "altered by the presenter's tamper control" from `demo.tamper_state`.
The shared and review screens show only the broken badge and the altered turn named by `brokenAt`, never a tamper label (like TDM-002's injection marking).

## Data Schemas

- `RecordEntry` (the IDR-003 `payload`): `{ entryId: string, kind: "turn" | "consent" | "amendment" | "confirmation" | "explain_back" | "interpreter_request", at: ISO-8601 string, body: object }`, where `body` is:
  - `turn`: the public CDR-002 `TurnCaption` plus `{ speaker, settledAs: "final" | "blocked" | "escalated", physicianName?, patientName? }`; never `emotion`, `certainty`, `backTranslation`, `confidence`, or an unspoken translation.
  - `consent`: CDR-005 `ConsentState` without `entryId`, plus `noticeSha256: string`.
  - `amendment`: `{ segmentId, amendmentId, replaces: "original" | amendmentId, sourceText, translation, toneLabel, criticalValues: CaptionCriticalValue[], by: "patient" }`.
  - `confirmation`: `{ segmentId, version: "original" | amendmentId, by: "patient" }`.
  - `explain_back`: CDR-005 `ExplainBackResult` without `entryId`.
  - `interpreter_request`: CDR-001 `interpreter.escalation` payload.
- `SegmentConfirm` (command): `{ segmentId: string, version: string }`.
- `SegmentAmend` (command): `{ segmentId: string, text: string (1 to 1000 characters), language: PatientLanguage, recognitionConfidence: number (0 to 1) }`.
- `SegmentStatus`: `{ segmentId: string, amendmentId: string, stage: "translating" | "verifying" | "retrying" | "applied" | "refused", reason?: "blocked" | "escalated" | "failed" }`.
- `SegmentAnalysis`: `{ segmentId: string, amendmentId: string, result: TurnResult }` (controller only).
- `segment.amended` payload (CDR-001 fields kept; new fields optional): `{ segmentId, by: "patient", action: "confirm" | "amend", newText?: string, amendmentId?: string, version?: string, translation?: string, toneLabel?: ToneLabel, criticalValues?: CaptionCriticalValue[], entryId?: string }`.
  For `amend`, `newText`, `amendmentId`, `translation`, and `entryId` are set; for `confirm`, `version` and `entryId` are set.
- `SegmentHistory`: `{ segmentId: string, original: TurnCaption, amendments: { amendmentId, sourceText, translation, toneLabel, criticalValues, at, entryId }[], confirmed: { version: string, at: string, entryId: string } | null, current: "original" | amendmentId }`.
- `TamperRecord` (command): `{ entryId: string }`.
- `TamperState`: `{ entryId: string, at: ISO-8601 string }` (controller only).
- `record.integrity` payload: unchanged CDR-001 shape `{ status, headHash, brokenAt? }`, with `brokenAt` defined as the failing entry's `entryId`.

## Evolution Strategy

Additive to CDR-001: `segment.amended` gains only optional fields, `visit.state` gains only optional fields, and new events are ignored by older screens.
`brokenAt` keeps its type and its meaning for turns; it now also names non-turn entries.
New `RecordEntry.kind` values are additive.
Physician corrections can be added later by allowing `by: "physician"` with a read-back step, without changing these shapes.
A product version replaces the in-memory chain (ADR-007) with persistent storage and external anchoring (IDR-003) without changing the channel.

## Testing Requirements

Contract tests in pytest and `npm run check:contracts` cover every new message, the extended `segment.amended`, and the `visit.state` additions.
Tests named for this record (for example `test_amendment_keeps_original_cdr_006`) cover:
- every settled turn, consent change, applied correction, confirmation, explain-back result, and interpreter request appends exactly one entry, and nothing else does;
- no chain payload contains `emotion`, `certainty`, `backTranslation`, `confidence`, or the translation of a blocked or escalated turn;
- a correction ending `final` appends an `amendment` entry, leaves the original `turn` entry and its hash untouched, and the history shows both, with verification still `verified`;
- a correction whose dose mismatches on both attempts is refused with `reason: "blocked"`, is never chained, and the review screen receives no translation;
- `segment.amend` refused for a physician turn, a blocked or escalated turn, a wrong language, a second correction in flight, and from controller and screen connections; the review sender gets `command.refused`;
- `segment.confirm` of a version that is no longer current is refused with `not_current`;
- `demo.tamper_record` refused outside presenter mode and from screen and review connections; when accepted, `record.integrity` turns `broken` with `brokenAt` equal to the altered turn's `segmentId`, and no screen or review connection receives `demo.tamper_state`, live or via `visit.state`;
- altering an amendment entry names the `amendmentId` in `brokenAt`;
- the role filter applies to `segment.analysis` and `segments[].amendments[].analysis` exactly as to `turn.analysis`.
A front-end test checks the review screen shows a corrected turn with its original in the history, and the shared screen shows the broken badge naming the turn with no tamper label.

## Consequences

- **Positive**: corrections and confirmations are tamper-evident like turns; the badge names the exact altered entry; the patient's corrections pass the same dose safety rules as live speech.
- **Negative**: the review screen needs speech recognition; corrections cost one turn graph run each.
- **Risks and mitigations**: a tamper control in production would be dangerous; it is gated by TDM-002's presenter mode and lapses with the demo, and the record view marks it.

## Implementation

Code governed by this record carries `@contract ws:/ws/visit` and `@implements CDR-006: Record chain entries, transcript review corrections, and the tamper control`.
Demo-night-mvp tasks 3.5 and 3.8 build it, after this record is accepted.

Open questions for the decision owner:
1. Should the physician also be able to correct their own turns in review (with read-back for critical values), or only the patient, as drafted?
2. Should interpreter requests and high-risk marks be chained, as drafted, given ADR-003 requires them in the transcript?
3. Is TDM-002's presenter gate enough for the tamper control, or should it have its own TDM with an expiry, like TDM-002?

## Review Notes

- 2026-11-08, Claude (agent): Drafted as a proposal for the supervising session, for demo-night-mvp tasks 3.5 and 3.8, including the hash chain agent's two gaps (no tamper command; index to `brokenAt` mapping). Awaiting human review; do not implement until accepted.
