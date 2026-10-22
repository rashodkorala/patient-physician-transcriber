---
id: adr-003
title: "Human interpreter escalation on low confidence and high-risk moments"
status: accepted
date: 2026-10-22
authors: ["rashodkorala"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: human
category: architecture
related_decisions: [mdd-001]
related_specs: [demo-consultation-flow, medical-interpretation]
related_changes: [add-multilingual-medical-consultation, demo-night-mvp]
ai_context:
  implementation_priorities:
    - "Offer a human interpreter when confidence is low or the moment is high risk"
  framework_hints:
    - "Demo: interpreter call is mocked with a connecting state"
  validation_rules:
    - "Escalation offer must appear in both languages"
    - "Escalation is recorded in the transcript"
affects: []
implementation_refs: []
test_refs: []
---

# ADR-003: Human interpreter escalation on low confidence and high-risk moments

## Summary

The system offers a qualified human interpreter whenever translation confidence is low or the visit reaches a high-risk moment (consent to procedures, serious diagnosis, end-of-life care, mental health crisis, safeguarding).

## Context

- **Technical drivers**: machine translation is weaker in low-resource languages and for high-stakes content.
- **Quality attributes**: clinical safety.
- **Constraints**: real interpreter integration is out of scope for the demo.

## Decision

The turn pipeline escalates when the confidence or tone check still fails after one retry; a critical value mismatch is blocked and the speaker asked to repeat instead of escalating (CDR-002); the physician can mark a moment as high risk; either party can request a human at any time. For the demo the call is simulated.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Only on request | Simple | Relies on people noticing errors they cannot see | Unsafe |
| Low confidence only | Automatic | Misses high-risk moments with confident but wrong output | Incomplete |

## Consequences

- **Positive**: credible safety story.
- **Negative**: real integration and cost later.
- **Risks and mitigations**: tune threshold during rehearsals.

## Implementation

Escalate node in the turn graph (ADR-004); escalation event in CDR-001; interpreter button on screens.

## Review Notes

- 2026-10-22, rashodkorala: Accepted by the project lead in the planning conversation.
- 2026-10-22, rashodkorala: Amended: automatic escalation covers confidence and tone failures only; critical value mismatches are blocked per CDR-002. Recorded by Claude (agent) at rashodkorala's explicit request.
