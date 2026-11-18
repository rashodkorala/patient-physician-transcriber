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
related_changes: [add-multilingual-medical-consultation, demo-night-mvp, mediator-voice, trust-across-the-barrier]
ai_context:
  implementation_priorities:
    - "A tone check that still fails after one retry escalates at once, because repeating does not repair a meaning drift"
    - "A confidence check that still fails after one retry yields an unclear turn (never spoken, never shown as a translation) and a spoken request to say it again; the third consecutive unclear turn from the same speaker escalates with reason low_confidence"
    - "Offer a human interpreter when the physician marks a moment high risk, or on request from either party at any time"
    - "Never escalate on a critical value mismatch; that turn is blocked (CDR-002)"
    - "Automatic detection of high-risk moments is not decided (see ADR-008, proposed)"
  framework_hints:
    - "Demo: interpreter call is mocked with a connecting state"
  validation_rules:
    - "Escalation offer must appear in both languages"
    - "Escalation is recorded in the transcript"
    - "The server keeps an unclear streak per speaker; any final or read-back-confirmed turn from that speaker resets it, and blocked turns do not change it"
    - "An unclear turn shows the original and a say-it-again notice in both languages, and the interpreter says that line aloud in the speaker's language"
affects: []
implementation_refs: []
test_refs: []
---

# ADR-003: Human interpreter escalation on low confidence and high-risk moments

## Summary

The system offers a qualified human interpreter when a turn's tone check still fails after one retry, when the same speaker has had three consecutive unclear turns, when the physician marks a moment as high risk (for example consent to a procedure, a serious diagnosis, end-of-life care, a mental health crisis, or a safeguarding concern), or when either party asks. A turn whose confidence check still fails after one retry is first treated as unclear: the speaker is asked, in both languages and aloud, to say it again, twice, before a human is offered. Critical value mismatches are blocked, not escalated. Automatic detection of high-risk moments is a separate, undecided safety question (ADR-008).

## Context

- **Technical drivers**: machine translation is weaker in low-resource languages and for high-stakes content.
- **Quality attributes**: clinical safety.
- **Constraints**: real interpreter integration is out of scope for the demo.

## Decision

A turn whose recognition or translation confidence is still below the threshold after the graph's one internal retry is not escalated at once. It gets the status `unclear` (CDR-002): never spoken, never shown as a translation, with the original and a say-it-again notice in both languages, and the interpreter says that line aloud in the speaker's language. The server keeps an unclear streak per speaker (patient, physician, companion). The first and second consecutive unclear turns from the same speaker are `unclear`; the third is `escalated` with reason `low_confidence`, and the human interpreter is offered. Any `final` or read-back-confirmed turn from that speaker resets the streak, and blocked turns do not change it. A tone failure after one retry still escalates at once (`tone_failure`), because repeating does not repair a meaning drift. A critical value mismatch is blocked and the speaker asked to repeat instead of escalating (CDR-002); the physician can mark a moment as high risk (CDR-001 `visit.mark_high_risk`); either party can request a human at any time. For the demo the call is simulated.

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
- 2026-11-10, rashodkorala: Extended to the trust-across-the-barrier change under the blanket authorisation given in session (see MDD-005). Recorded by Claude (agent) at rashodkorala's explicit request.
- 2026-11-12, rashodkorala: Amended: low confidence yields an unclear turn and a spoken request to say it again, twice; the third consecutive unclear turn from the same speaker escalates with reason low_confidence; tone failures escalate at once as before. Recorded by Claude (agent) at rashodkorala's explicit request under the blanket authorisation (see MDD-005).
- 2026-11-16, rashodkorala: amended ("Deliver with a note"). A relay that still uses "he" or "she" for a patient or companion whose gender was never stated, after one retry, does not escalate: it is delivered, and the controller is told privately that the gender was not stated.
  A guessed pronoun does not change a dose or an instruction, and escalation stays for a change of meaning (tone failure) and for repeated low confidence, as decided above.
  Recorded by Claude (agent) at rashodkorala's explicit request. The status stays accepted.
