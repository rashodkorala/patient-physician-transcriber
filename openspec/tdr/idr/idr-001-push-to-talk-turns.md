---
id: idr-001
title: "Push-to-talk per speaker instead of diarisation"
status: proposed
date: 2026-10-22
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: implementation
related_decisions: [adr-005, mdd-003]
related_specs: []
related_changes: [demo-night-mvp]
ai_context:
  implementation_priorities:
    - "Controller has a button per speaker; speaker and language are known per turn"
  framework_hints:
    - "Recognition starts on press and ends on release or silence"
  validation_rules:
    - "Every turn records speaker and language explicitly"
affects: [web/app/control/]
implementation_refs: []
test_refs: []
---

# IDR-001: Push-to-talk per speaker instead of diarisation

## Summary

The physician controller has 'Physician speaking' and 'Patient speaking' buttons, so each turn's speaker and language are known without automatic diarisation.

## Context

- **Feature or component**: turn capture on `/control`.
- **Technical requirements**: correct speaker labels in the transcript and note.
- **Constraints**: diarisation in a live room is the biggest demo risk.

## Decision

Use push-to-talk per speaker for the demo. The roadmap's automatic diarisation remains a later change.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Automatic diarisation | Hands-free | Error-prone live; mislabels break provenance | Too risky for demo |

## Consequences

- **Positive**: reliable labels.
- **Negative**: physician presses buttons for both speakers.
- **Risks and mitigations**: large buttons and keyboard shortcuts.

## Implementation

`web/app/control/` push-to-talk component sending `turn.submit` (CDR-001).

## Review Notes

- 2026-10-22, Claude (agent): Drafted as a proposal. Awaiting human review; do not implement until accepted.
