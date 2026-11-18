---
id: idr-008
title: "Physician review of low-confidence speech before submission"
status: accepted
date: 2026-11-17
authors: ["Codex (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala"
proposed_by: agent
category: implementation
related_decisions: [adr-003, cdr-002, idr-001, idr-004, idr-007]
related_specs: [demo-consultation-flow]
related_changes: [demo-night-mvp]
ai_context:
  implementation_priorities:
    - "Show low-confidence microphone text privately on the physician controller before it is submitted"
    - "Send only the physician-reviewed text through the same path as typed input"
  framework_hints:
    - "Reuse the typed-turn path and existing role and language selection"
    - "Use the existing 0.70 threshold and keep the visit protocol unchanged"
  validation_rules:
    - "A matching but low-scored English capture can be confirmed for French translation"
    - "An unconfirmed capture never reaches the shared screen or translation service"
    - "Confirmation still triggers translation confidence checks and dose blocking or read-back"
    - "Clear pending review when a visit resets, pauses, or loses consent"
affects: [web/components/Controller.tsx, web/components/controller.module.css]
implementation_refs: []
test_refs: []
---

# IDR-008: Physician review of low-confidence speech before submission

## Summary

Let the physician review a captured transcript before submitting it when speech recognition reports a score below 0.70.

## Context

In the French demo visit, the English original matched the script in three consecutive turns with combined scores below 0.70.
Retrying translation cannot raise a speech-recognition score for an unchanged capture.

## Decision

For demo push-to-talk, show a private, editable transcript when a nonempty capture has a positive recognition score below 0.70.
Offer confirmation or discard.
Submit the confirmed text as physician-reviewed input for the original speaker through the existing typed-turn flow.
Keep translation confidence checks, deterministic checks, and physician dose read-back.
Preserve existing handling of unknown scores and hands-free input.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Lower the confidence threshold | Fewer interruptions | Releases more unreviewed captures | Review lets the physician check the actual transcript |
| Keep manual copy into the typed-turn box | Already available | Slower during the demo | Inline review removes the copy step |

## Consequences

Low-scored speech requires one confirmation before translation.
The physician has a chance to fix words and numbers in the original before any translation is shown.

## Implementation

Add the review panel beside the speaking controls and verify the English-to-French demo flow, including a dose that still requires confirmation.

## Review Notes

- 2026-11-17, rashodkorala: Accepted. Recorded by Codex at rashodkorala’s explicit request.

- 2026-11-17, Codex: Drafted after the project lead requested inline review.
