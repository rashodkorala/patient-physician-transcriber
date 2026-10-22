---
id: adr-008
title: "Automatic high-risk moment detection: suggest only"
status: proposed
date: 2026-10-22
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: architecture
related_decisions: [adr-003]
related_specs: [medical-interpretation]
related_changes: [add-multilingual-medical-consultation]
ai_context:
  implementation_priorities:
    - "Detection may only suggest a high-risk mark to the physician"
    - "The physician's mark, not the detector, triggers escalation"
  framework_hints:
    - "Classifier over each turn's original and translation; categories: procedure consent, serious diagnosis, end-of-life care, mental health crisis, safeguarding"
  validation_rules:
    - "Never escalate, label the record, or alert anyone other than the physician on detection alone"
    - "Suggestions and the physician's response are recorded in the audit trail"
    - "Safeguarding and crisis suggestions are never shown on shared screens"
affects: []
implementation_refs: []
test_refs: []
---

# ADR-008: Automatic high-risk moment detection: suggest only

## Summary

If adopted, the product would detect possible high-risk moments and suggest to the physician, privately, that they mark the moment high risk. Detection would never escalate, label the record, or notify anyone on its own.

## Context

- **Technical drivers**: physicians may not think to mark a high-risk moment mid-conversation; the roadmap spec originally required automatic detection with no decision behind it.
- **Quality attributes**: clinical safety, patient privacy, and avoiding false alarms in front of the patient.
- **Constraints**: crisis and safeguarding detection is a safety decision in its own right; false positives on a shared screen could harm trust or disclose sensitive concerns.

## Decision

Proposed: a private, suggest-only detector. When a turn looks like procedure consent, a serious diagnosis, end-of-life care, a mental health crisis, or a safeguarding concern, the physician's controller shows a suggestion to mark the moment high risk. Only the physician's mark (ADR-003, CDR `visit.mark_high_risk` or its product equivalent) triggers the interpreter offer. Before acceptance: define categories with a clinician, measure precision and recall on scripted consultations, and complete a safety and privacy review.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| No automatic detection | Simplest; no false alarms | Relies entirely on the physician remembering | Kept as fallback if evaluation fails |
| Automatic escalation on detection | Fast | False positives interrupt visits and may disclose sensitive concerns | Unsafe without human judgement |
| Visible alerts on shared screens | Transparent | Discloses crisis or safeguarding suspicions in front of others | Privacy risk |

## Consequences

- **Positive**: helps physicians notice moments that need a qualified interpreter.
- **Negative**: model work, evaluation, and clinical sign-off.
- **Risks and mitigations**: suggest-only and controller-only limit harm from false positives; misses are covered by physician marking and the always-available interpreter button.

## Implementation

Not for the demo. Product only, after the roadmap is unparked and this record is accepted; until then the roadmap spec requires physician marking only.

## Review Notes

- 2026-10-22, Claude (agent): Drafted as a proposal. Awaiting human review; do not implement until accepted.
