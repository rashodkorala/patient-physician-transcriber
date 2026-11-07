---
id: cdr-003
title: "Participant names and interpreter lines on the visit channel"
status: accepted
date: 2026-11-03
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: contract
related_decisions: [cdr-001, cdr-002, mdd-004, adr-009, adr-007]
related_specs: [visit-introduction, interpreter-voice]
related_changes: [mediator-voice, orb-speaking-state]
ai_context:
  implementation_priorities:
    - "Additive to CDR-001: new commands and events only; no existing event changes shape except new optional fields"
    - "Names travel in visit.state for every role, because the shared screen shows them"
  framework_hints:
    - "Pydantic models in server/contracts.py; TypeScript in web/lib/contracts.ts; regenerate web/lib/generated/"
  validation_rules:
    - "Names are trimmed, at most 60 characters, and never required to start a turn"
    - "A name proposed from speech is applied only after the controller confirms it"
    - "Speech audio is fetched by id; the server refuses an id that is not a settled, spoken turn or an interpreter line"
affects: [server/contracts.py, web/lib/contracts.ts, server/main.py]
implementation_refs: []
test_refs: []
---

# CDR-003: Participant names and interpreter lines on the visit channel

## Summary

Adds participant names, the interpreter's own spoken lines, and a speak-by-id audio endpoint to the visit contract, additively to CDR-001.

## Context

- **Technical drivers**: MDD-004 needs names in every turn and an opening introduction; ADR-009 moves synthesis to the server.
- **Constraints**: no database (ADR-007); the saved default physician name lives on the controller device.

## Decision

Extend the visit channel additively with name commands and events, interpreter lines, and a speak-by-id audio endpoint that only serves checked content.

## Contract Specification

Commands (client to server):

| Command | Sender |
|---|---|
| `visit.set_names` (optional `physicianName`, optional `patientName`) | Controller; allowed at any time |
| `visit.start_introduction` | Controller; rejected once the visit has a turn |
| `visit.name_reply` (`role`: `physician` or `patient`, recognised text) | Controller, during the introduction |
| `visit.name_confirm` / `visit.name_reject` (`role`) | Controller |

Events (server to clients):

| Event | When |
|---|---|
| `interpreter.line` (`lineId`, `purpose`: `introduction`, `ask_physician_name`, `ask_patient_name`, `welcome`; `text` and `language` per language) | The interpreter says something of its own; every role |
| `visit.name_proposed` (`role`, `name`) | *Controller only.* A name heard in a reply, waiting for confirmation |
| `visit.names` (`physicianName`, `patientName`, both nullable) | Names changed; every role |

`visit.state` gains `physicianName`, `patientName`, and `introduction` (`pending`, `asking_physician`, `asking_patient`, `done`, `skipped`) for every role.

HTTP: `GET /api/speech/{id}` streams audio for a settled `final` turn, a confirmed read-back turn, or an `interpreter.line`; any other id returns 404.
Tone instructions are built on the server from the turn's emotion and certainty, so they never reach shared screens.

## Data Schemas

- `Names`: `{ physicianName: string | null, patientName: string | null }`, each trimmed, 1 to 60 characters, no digits.
- `InterpreterLine`: `{ lineId: string, purpose: "introduction" | "ask_physician_name" | "ask_patient_name" | "welcome", lines: { language: Language, text: string }[] }`.
- `NameProposed`: `{ role: "physician" | "patient", name: string }`.
- `IntroductionState`: `"pending" | "asking_physician" | "asking_patient" | "done" | "skipped"`.

## Evolution Strategy

Additive to CDR-001: existing events keep their shape, and new `visit.state` fields are optional so older clients ignore them.
A later accounts system can replace the device-saved default without changing these messages.

## Testing Requirements

Contract tests in pytest and `npm run check:contracts` cover every new message, the name limits, and that `/api/speech/{id}` returns 404 for blocked, escalated, rejected, unsettled, and unknown ids.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Browser sends text to a speak endpoint | Simple | Any text can be spoken; bypasses checks | Breaks the speak-only-checked rule |
| Names only on the controller | Fewer events | Shared screen cannot say who spoke | Captions need names |

## Consequences

- **Positive**: the server is the single gate for what is spoken.
- **Negative**: more commands and a small introduction state machine.
- **Risks and mitigations**: misheard names, mitigated by controller confirmation and typing.

## Implementation

The `mediator-voice` change, task groups 1 and 3.

## Review Notes

- 2026-11-03, Claude (agent): Drafted as a proposal for the `mediator-voice` change. Awaiting human review; do not implement until accepted.
- 2026-11-03, rashodkorala: Accepted in session. Recorded by Claude (agent) at rashodkorala's explicit request.
