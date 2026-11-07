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
related_decisions: [mdd-001, adr-008]
related_specs: [demo-consultation-flow, medical-interpretation]
related_changes: [add-multilingual-medical-consultation, demo-night-mvp, mediator-voice]
ai_context:
  implementation_priorities:
    - "Offer a human interpreter when the confidence or tone check still fails after one retry, when the physician marks a moment high risk, or on request"
    - "Never escalate on a critical value mismatch; that turn is blocked (CDR-002)"
    - "Automatic detection of high-risk moments is not decided (see ADR-008, proposed)"
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

The system offers a qualified human interpreter when a turn's confidence or tone check still fails after one retry, when the physician marks a moment as high risk (for example consent to a procedure, a serious diagnosis, end-of-life care, a mental health crisis, or a safeguarding concern), or when either party asks. Critical value mismatches are blocked, not escalated. Automatic detection of high-risk moments is a separate, undecided safety question (ADR-008).

## Context

- **Technical drivers**: machine translation is weaker in low-resource languages and for high-stakes content.
- **Quality attributes**: clinical safety.
- **Constraints**: real interpreter integration is out of scope for the demo.

## Decision

The turn pipeline escalates when the confidence or tone check still fails after one retry; a critical value mismatch is blocked and the speaker asked to repeat instead of escalating (CDR-002); the physician can mark a moment as high risk (CDR-001 `visit.mark_high_risk`); either party can request a human at any time. For the demo the call is simulated.

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
- 2026-10-22, rashodkorala: Summary and ai_context brought in line with the decision paragraph (they still described escalation as confidence and high-risk only); physician marking now has a CDR-001 command; automatic detection referred to ADR-008. Recorded by Claude (agent) at rashodkorala's explicit request.
- 2026-11-03, rashodkorala: Extended to the mediator-voice change. Recorded by Claude (agent) at rashodkorala's explicit request.
