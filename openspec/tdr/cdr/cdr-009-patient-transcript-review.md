---
id: cdr-009
title: "Patient confirmation of a captured transcript before translation"
status: accepted
date: 2026-11-18
authors: ["Codex (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala"
proposed_by: agent
category: api-contract
related_decisions: [adr-003, adr-007, cdr-001, cdr-005, cdr-006, idr-008]
related_specs: [demo-consultation-flow]
related_changes: [demo-night-mvp]
ai_context:
  implementation_priorities:
    - "Offer a patient-language review for low-confidence patient push-to-talk captures before submitting them for translation"
    - "Keep the original transcript private to the physician and patient views"
  framework_hints:
    - "Use the visit channel and an opaque review identifier; bind each action to the current visit and pending capture"
  validation_rules:
    - "Confirm submits the reviewed original text once; repeat clears it without submitting"
    - "Pause, withdrawal and a new visit clear the pending review"
    - "The shared screen never receives the unconfirmed transcript"
    - "Translation confidence and critical-value checks still run"
affects: [server/main.py, server/contracts.py, web/components/Controller.tsx, web/components/PatientScreen.tsx]
implementation_refs: []
test_refs: []
---

# CDR-009: Patient confirmation of a captured transcript before translation

## Summary

Let the patient confirm what the app heard or ask to say it again before a low-confidence patient capture is translated.

## Context

The patient can already confirm saved turns.
Before translation, the pending capture is local to the physician controller under IDR-008 and has no settled record entry.

## Decision

Use a visit-scoped pending review for the patient’s low-confidence push-to-talk capture.
Deliver the original text to the patient review view and physician controller.
Show the patient **Yes, that’s what I said** and **Let me say it again** in their selected language.
Confirmation releases the reviewed original text through the existing translation checks, once per capture.
Repeating clears the review and waits for a fresh capture.
Reject stale replies and clear pending review on pause, consent withdrawal, or visit reset.
Physician review remains available and resolves the same pending capture once.
The shared screen receives only the existing post-submission events.

## Contract Specification

The controller sends `transcript.review_start` with the captured text.
The server publishes `transcript.review_state` to controller and review connections and restores it in their visit snapshots.
Either role sends `transcript.review_resolve` to confirm or repeat.
Only the controller can supply edited text when confirming.
The server clears the pending review before processing a confirmed turn so concurrent replies cannot submit it twice.

## Data Schemas

- Start requires `text` as a nonempty string in the current patient's language.
- State carries a nullable `review` with required string fields `reviewId`, `text`, and `language`.
- Resolve requires string `reviewId` and `action` of `confirm` or `repeat`, with optional controller-only string `text`.

## Evolution Strategy

Add commands, events, and an optional snapshot field to the existing visit channel.
Existing microphone submissions remain valid.

## Testing Requirements

Verify role visibility, patient confirmation, repeat, concurrent resolution, and clearing on pause, consent withdrawal, and reset.
Verify that a confirmed turn still uses the normal translation checks.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Reuse settled transcript confirmation | Existing controls | It runs after translation and requires a saved turn | The requested confirmation happens before translation |

## Consequences

The patient can verify their own words without needing the physician to read French.
A low translation confidence score can still hold back the translation.

## Implementation

Add role-filtered visit commands and events for pending review.
Reuse patient-language labels and verify privacy, duplicate handling, and cancellation in the demo flow.

## Review Notes

- 2026-11-18, Codex: Drafted after the project lead requested patient confirmation.

- 2026-11-18, rashodkorala: Accepted. Recorded by Codex at rashodkorala’s explicit request.
