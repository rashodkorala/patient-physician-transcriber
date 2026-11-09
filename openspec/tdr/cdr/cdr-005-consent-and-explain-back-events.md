---
id: cdr-005
title: "Consent and explain-back on the visit channel"
status: accepted
date: 2026-11-08
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: api-contract
related_decisions: [mdd-001, mdd-003, adr-001, adr-007, adr-011, cdr-001, cdr-002, cdr-003, cdr-004, cdr-006, idr-003, idr-004]
related_specs: [demo-consultation-flow]
related_changes: [demo-night-mvp]
ai_context:
  implementation_priorities:
    - "Additive to CDR-001: new commands and events and new optional visit.state fields; no existing message changes shape"
    - "The server is the only gate: it refuses every speech-capturing command until consent is given"
    - "Explain-back results are controller only; the shared screen sees only a content-free state"
    - "The interpreter's introduction (CDR-003) starts only after consent"
    - "The consent notice is read aloud in the patient's language through the CDR-003 speak gate and CDR-004 playback"
  framework_hints:
    - "Pydantic models in server/contracts.py; TypeScript in web/lib/contracts.ts; regenerate web/lib/generated/"
    - "Add controller-only commands to CONTROLLER_COMMANDS and the new controller-only event to CONTROLLER_ONLY_EVENTS"
    - "Add a REVIEW_OR_CONTROLLER_COMMANDS set so a screen connection's copy of a consent command is dropped"
    - "Consent notice text lives on the server, one reviewed file per language, so every screen shows identical words"
  validation_rules:
    - "turn.submit, visit.start_introduction, and visit.name_reply are refused while visit.state.consent is null"
    - "consent.give is accepted only for the current notice version in the visit's patient language"
    - "consent.give from the controller is recorded as physician_on_behalf; from review as patient"
    - "GET /api/speech/consent-{noticeId} serves the current notice only, in the visit's patient language only"
    - "visit.set_languages is refused while consent is given"
    - "explainback.result never reaches screen or review connections, live or via visit.state"
    - "explainback.state carries no text, items, or outcomes"
    - "Code-checked explain-back items keep the code's outcome; the model cannot override it (ADR-011)"
    - "Every consent change and every explain-back result is appended to the record chain, never edited (CDR-006, IDR-003)"
affects: [server/contracts.py, server/main.py, server/visit_store.py, server/introduction.py, web/lib/contracts.ts, web/lib/generated/, web/components/Controller.tsx, web/components/SharedScreen.tsx]
implementation_refs: []
test_refs: []
---

# CDR-005: Consent and explain-back on the visit channel

> Contract Decision Record. Only a human may set `status: accepted`.

## Summary

Adds the commands and events for two in-visit beats of the demo (MDD-003): consent in the patient's language before the conversation starts (beat 2, task 3.2), and the explain-back check where the patient repeats the plan and the physician sees what was matched, missed, or contradicted (beat 5, task 3.4).
It also adds `command.refused`, a content-free refusal that a review connection can receive, because CDR-001's `error` is controller only.
Additive to CDR-001, in the same way as CDR-003 and CDR-004.

## Context

- **Integration point**: server (ADR-001) to the controller, the shared screen, and the review screen over `ws:/ws/visit`.
- **Related decisions**: CDR-001 already carries `consent` in both `visit.state` shapes but defines no command to give, record, or withdraw it; it has no explain-back messages at all.
  ADR-011 (proposed alongside this record) decides how the explain-back comparison is made; this record only fixes the messages.
  CDR-006 (proposed alongside this record) defines the record chain entries this record appends.
- **Requirements**: the spec says the system SHALL NOT start the conversation until the patient taps to consent, and records the consent time; the physician SHALL see which instructions were matched, missed, or contradicted, and a missed frequency is flagged.
- **Constraints**: the shared screen (`/screen`) is a TV with no input (task 4.2), so the patient's tap comes from the review screen (patient's phone) or, when there is no phone, from the controller on the patient's behalf.
  Continuous listening (IDR-004) splits one spoken explanation into several turns on silence, so the explanation cannot be "the next turn".

## Decision

1. **Consent is a server-held gate.**
   The server holds a reviewed consent notice per patient language and publishes it in `visit.state`.
   Consent is given by `consent.give` and withdrawn by `consent.withdraw`, from the review screen or the controller.
   While consent is not given, the server refuses every command that captures speech.
   The physician may give consent on the patient's behalf from the controller, and the record says so (`physician_on_behalf`).
2. **The notice is read aloud.**
   The controller plays the notice in the patient's language through the existing speak gate (CDR-003) and playback reports (CDR-004), with speech id `consent-{noticeId}`.
3. **The interpreter's introduction comes after consent.**
   `visit.start_introduction` is refused until consent is given.
   This changes how the `mediator-voice` flow opens: language, then consent, then the interpreter introduces itself and asks for names.
4. **Explain-back is a bracketed mode.**
   The physician opens it with `explainback.start`, the patient speaks one or more ordinary patient turns (interpreted and spoken as usual), and the physician closes it with `explainback.check`, which runs the comparison over those turns.
   `explainback.cancel` closes it without a check.
5. **Explain-back results are private to the physician.**
   The full result goes only to controller connections; the patient does not see the outcome on any screen.
   Every role sees a content-free `explainback.state`, so the shared screen can prompt the patient without showing a score.
6. **Both beats append to the record.**
   Consent changes and explain-back results are new chain entries (CDR-006); nothing is edited in place.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Consent only in the browser (hide the conversation screen until tapped) | No contract change | The server would still accept turns, so a second tab or replay could capture speech without consent; no recorded time | The gate must sit where turns are accepted |
| Consent notice text in `web/i18n` with a version string | Reuses the existing i18n files | Two screens could render different words for the same version; the record could not hold what was shown | One server-held text is simpler to review and hash |
| Consent only from the review screen | The patient's own tap, always | The demo may run without a phone; the beat would fail | The review screen is the preferred path; the physician may give consent on the patient's behalf, recorded as `physician_on_behalf` |
| Consent notice shown only, not read aloud | No speech needed before consent | A patient who cannot read the script well cannot consent with understanding | Read aloud in the patient's language through the existing speak gate |
| Introduction before consent | The interpreter introduces itself and then asks for consent | The introduction captures speech (names) before consent | Introduction after consent |
| Explain-back on the next single patient turn | Smallest | Continuous listening (IDR-004) splits an explanation on pauses; half an explanation would be scored | Bracketing with start and check fits both push-to-talk and hands-free |
| Explain-back result on every screen | Patient sees it too | A "missed" list on a TV can embarrass the patient; MDD-001 treats feedback about communication as private by default | Physician sees it and re-explains; the project lead may widen this |
| A separate explain-back recording path (not a turn) | Keeps the explanation out of the conversation | The physician would not hear the explanation interpreted; two capture paths to keep safe | The explanation is part of the conversation and the record |

## Contract Specification

### Commands (client to server)

| Command | Sender | Server rule |
|---|---|---|
| `consent.give` (`noticeVersion`, `language`) | Review or controller; a screen's copy is dropped | Accepted only if consent is not already given, `language` is the visit's patient language, and `noticeVersion` is the current version for that language. Records `by: "patient"` from a review connection and `by: "physician_on_behalf"` from a controller connection |
| `consent.withdraw` (optional `reason`) | Review or controller; a screen's copy is dropped | Accepted only while consent is given. Takes effect at once (see withdrawal rules) |
| `consent.read_aloud` | Review or controller; a screen's copy is dropped | Accepted while a notice is set for the visit. Publishes `consent.speak` to controllers |
| `explainback.start` | Controller | Refused unless consent is given, the visit is not paused, no read-back is pending, no explain-back is open, and at least one physician turn has been spoken (settled `final` or read-back confirmed) |
| `explainback.check` (`explainBackId`) | Controller | Refused unless that explain-back is open in `listening` and at least one patient turn has settled as `final` since it opened |
| `explainback.cancel` (`explainBackId`) | Controller | Refused unless that explain-back is open in `listening` |

### Events (server to clients)

| Event | Who receives it | When |
|---|---|---|
| `consent.changed` (`ConsentState`) | Every role | Consent was given or withdrawn |
| `consent.speak` (`ConsentSpeak`) | *Controller only* | The notice should be played: once automatically when a notice is first set and consent is not given, and again on each `consent.read_aloud` |
| `explainback.state` (`ExplainBackState`) | Every role | An explain-back opened, moved to checking, finished, failed, or was cancelled |
| `explainback.result` (`ExplainBackResult`) | *Controller only* | The check finished |
| `command.refused` (`CommandRefused`) | Only the review connection that sent the refused command | A review connection's command was refused; controller connections keep receiving CDR-001 `error` |

### `visit.state` additions (all optional)

- Every role: `consentNotice: ConsentNotice | null` for the visit's patient language, `consentState: ConsentState | null`, and `explainBack: ExplainBackState | null` for the latest explain-back.
- Controller only: `explainBackResults: ExplainBackResult[]`, oldest first.
- The existing `consent` field keeps its CDR-001 meaning and type (`string | null`): the ISO-8601 time the current consent was given, or `null` when consent is not given.

### Consent rules

1. **Blocked until consent.** While `consent` is `null`, the server refuses `turn.submit`, `visit.start_introduction`, and `visit.name_reply` (CDR-003) with `error` "Consent is needed before the conversation starts".
   The interpreter's introduction therefore always follows consent.
   `visit.set_languages`, `visit.set_names` (typed names), and all read-only messages stay allowed, so the physician can set up the visit.
2. **Languages lock with consent.** `visit.set_languages` is refused while consent is given, because consent was given to a notice in one language.
   Withdrawing consent unlocks it.
3. **Withdrawal stops capture at once.**
   - A read-back that is pending is discarded unspoken, exactly as `turn.readback_reject` (CDR-001).
   - A turn still in the turn graph is discarded when it finishes: it is never spoken, never published in `turn.result`, and never chained; the controller sees `turn.status` stage `discarded`.
   - An open explain-back is cancelled.
   - Turns already settled stay in the record; withdrawal is not erasure.
     Erasure is a product privacy question outside the demo (MDD-003).
4. **Consent can be given again** after withdrawal, which appends a new entry; the earlier entries stay.
5. **The notice is server-held.**
   Each live patient language (Punjabi, French, and Tamil per TDM-004, and Sinhala in test mode per TDM-003) has one reviewed notice file with a version.
   `ConsentNotice` carries the patient-language text and the English text, so the shared screen shows both.
   The text's SHA-256 is stored in the chain entry, so the record shows exactly what was agreed to.
6. **The notice is read aloud.**
   - Speech id: `consent-{noticeId}`, for example `consent-pa-IN-v1` (at most 64 characters, CDR-004).
   - `GET /api/speech/consent-{noticeId}?language={patientLanguage}` (CDR-003) serves the patient-language text of the visit's current notice, with the interpreter-line delivery; any other notice id or language returns 404.
   - CDR-004 rule 2 accepts `voice.started` for that id and language, because the gate allows it, so the shared screen shows the interpreter speaking.
   - The gate serves the notice whether or not consent is given; it is not captured speech.

### Explain-back rules

1. **Opening freezes the plan.**
   On `explainback.start` the server freezes the plan sources: every physician turn spoken so far, using its effective text (the latest applied correction, per CDR-006) and its critical values.
   Turns that were blocked, escalated, rejected, or discarded are never plan sources.
2. **The explanation is ordinary turns.**
   While `listening`, patient turns go through the turn graph and are spoken and captioned as usual.
   Only patient turns that settle as `final` count as the explanation; blocked or escalated patient turns do not count, so the patient can repeat.
   Physician turns during `listening` are allowed and recorded but never count as the explanation.
3. **Checking.**
   `explainback.check` moves the state to `checking`, runs the comparison defined by ADR-011, and then publishes `explainback.result` to controllers and `explainback.state` `done` to every role.
   While `checking`, new turns are accepted but do not join the explanation.
   If the comparison fails (model error or invalid output after one retry), the state becomes `failed` and the controller receives `error`; nothing is chained.
4. **Outcomes.**
   Each plan item has exactly one outcome: `matched`, `missed`, or `contradicted`.
   Items derived from critical values (`decidedBy: "code"`) are compared by code; the model never changes their outcome (ADR-011).
   A frequency that the explanation omits is therefore always `missed`, and a different frequency for the same medication is `contradicted`.
5. **Recorded.** A finished result is appended to the chain as an `explain_back` entry (CDR-006).

## Data Schemas

- `ConsentNotice`: `{ noticeId: string, speechId: string, version: string, language: PatientLanguage, lines: { language: Language, text: string }[] }`; `lines` holds the patient language first and English second.
  `noticeId` is `{language}-v{version}`, for example `pa-IN-v1`, so it changes whenever the text changes.
  `speechId` is `consent-{noticeId}`, so screens and the controller use one id.
- `ConsentSpeak`: `{ speechId: string, language: PatientLanguage }`, where `speechId` is `consent-{noticeId}`.
- `ConsentGive` (command): `{ noticeVersion: string, language: PatientLanguage }`.
- `ConsentWithdraw` (command): `{ reason?: string }`, at most 200 characters, stored in the record only.
- `ConsentState`: `{ state: "given" | "withdrawn", at: ISO-8601 string, by: "patient" | "physician_on_behalf", noticeId: string, noticeVersion: string, language: PatientLanguage, entryId: string }`.
  `entryId` is the chain entry id of this change (CDR-006).
- `ExplainBackRef` (command payload of `explainback.check` and `explainback.cancel`): `{ explainBackId: string }`.
- `ExplainBackState`: `{ explainBackId: string, state: "listening" | "checking" | "done" | "failed" | "cancelled", explanationTurnIds: string[] }`.
  Turn ids are already public through `turn.result`; no text, items, or outcomes.
- `ExplainBackItem`: `{ itemId: string, kind: "dose" | "frequency" | "medication" | "number" | "date" | "instruction" | "warning" | "follow_up", instruction: string, sourceTurnIds: string[], outcome: "matched" | "missed" | "contradicted", decidedBy: "code" | "model", expected?: string, heard?: string, evidenceTurnIds: string[] }`.
  `instruction` is in the physician's language; `expected` and `heard` are set for code-decided items (the normalised value expected and the value found, if any).
- `ExplainBackResult`: `{ explainBackId: string, planHeadHash: string, explanationTurnIds: string[], items: ExplainBackItem[], entryId: string }`.
  `planHeadHash` is the chain head when the plan was frozen.
- `CommandRefused`: `{ command: string, reason: "consent_required" | "consent_already_given" | "consent_not_given" | "wrong_notice" | "wrong_language" | "not_allowed" | "not_found" | "not_current" | "busy" | "invalid" }`; no free text, so nothing private can leak.

## Evolution Strategy

Additive to CDR-001: existing events keep their shape, the new `visit.state` fields are optional, and older screens ignore unknown event types.
The existing `consent` field keeps its type and meaning.
New `CommandRefused.reason` values and new `ExplainBackItem.kind` values are additive; renaming or removing one needs a superseding CDR.
A product version with accounts can bind consent to an identified patient without changing these messages.

## Testing Requirements

Contract tests in pytest and `npm run check:contracts` cover every new message and `visit.state` field.
Channel tests (named for this record, for example `test_consent_blocks_turns_cdr_005`) cover:
- `turn.submit`, `visit.start_introduction`, and `visit.name_reply` refused before consent and accepted after;
- `consent.give` refused for a wrong language, a stale notice version, a second give, and from a screen connection (dropped, no effect);
- `consent.give` from review recorded as `by: "patient"` and from the controller as `by: "physician_on_behalf"`, each with a chain entry;
- `visit.set_languages` refused while consent is given and accepted after withdrawal;
- `GET /api/speech/consent-{noticeId}` serves the current notice in the patient's language, returns 404 for English, an old version, or an unknown id, and `voice.started` is accepted for it;
- `consent.speak` is sent to controllers once when the notice is first set and again on `consent.read_aloud`, and never to screen or review connections;
- withdrawal during a pending read-back discards it unspoken; withdrawal during a turn in the graph discards that turn with no `turn.result`, no speech id allowed by the speak gate, and no chain entry;
- a review connection receives `command.refused` and never `error`;
- `explainback.start` refused without consent, while paused, during read-back, with nothing spoken by the physician, and when one is open;
- a fixture plan with "500 milligrams twice a day" and an explanation that says only "500 milligrams" yields the frequency item `missed` with `decidedBy: "code"`, even when the mocked model says `matched`;
- an explanation saying "once a day" for the same plan yields `contradicted`;
- blocked and escalated patient turns during `listening` are not in `explanationTurnIds`;
- `explainback.result` never reaches a screen or review connection, live or via `visit.state`, and `explainback.state` carries no text;
- a `screen` that connects mid explain-back receives `explainBack` with state only.
A front-end test checks the shared screen shows the consent notice in both languages until consent, and an explain-back prompt in both languages while `listening`.

## Consequences

- **Positive**: consent is enforced where turns enter, recorded with the exact notice, and withdrawable; explain-back works with both push-to-talk and hands-free capture, and a missed dose or frequency cannot be hidden by a lenient model.
- **Negative**: more commands and a small explain-back state machine; a review-screen refusal event in addition to `error`; reviewed consent text is needed in every live language.
- **Risks and mitigations**: the physician could tap consent for the patient; mitigated by recording `physician_on_behalf` in the record and preferring the review screen.
  The introduction (CDR-003) now waits for consent, which changes the opening of the `mediator-voice` flow: its controller must show consent before offering the introduction, and its tests must give consent first.

## Implementation

Code governed by this record carries `@contract ws:/ws/visit` and `@implements CDR-005: Consent and explain-back on the visit channel`.
Demo-night-mvp tasks 3.2 and 3.4 build it, after this record and ADR-011 and CDR-006 are accepted.

Decisions settled by the decision owner (relayed by the supervising session, 2026-11-09): the introduction comes after consent; the physician may consent on the patient's behalf, recorded as `physician_on_behalf`; only the controller sees the explain-back outcome; the notice is read aloud in the patient's language.

## Review Notes

- 2026-11-08, Claude (agent): Drafted as a proposal for the supervising session, for demo-night-mvp tasks 3.2 and 3.4. Awaiting human review; do not implement until accepted.
- 2026-11-09, Claude (agent): Revised to state rashodkorala's answers to the open questions, relayed by the supervising session. Still proposed; awaiting human review.
- 2026-11-09, rashodkorala: Accepted, with the supervising session's recommended answers to the open questions ("yes to all, merge and push, accept with your recommendations"). Recorded by Claude (agent) at rashodkorala's explicit request.
