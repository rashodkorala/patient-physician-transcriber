---
id: mdd-003
title: "Demo night scope: nine-beat script with Punjabi and French pairs"
status: accepted
date: 2026-10-22
authors: ["rashodkorala"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: human
category: strategy
related_decisions: [mdd-001]
related_specs: [demo-consultation-flow]
related_changes: [demo-night-mvp]
ai_context:
  implementation_priorities:
    - "Make the nine demo beats work reliably on the night"
    - "Punjabi to English and French to English only"
  framework_hints:
    - "Run locally on the demo laptop; no cloud deployment"
  validation_rules:
    - "Anything outside the nine beats is out of scope unless a human approves it"
affects: []
implementation_refs: []
test_refs: []
---

# MDD-003: Demo night scope: nine-beat script with Punjabi and French pairs

## Summary

Demo night on 19 November 2026 shows nine beats live for Punjabi to English and French to English; everything else is deferred.

## Context

- **Business Context**: a demo night audience, not clinical users. It must work and convince, not pass approvals.
- **Strategic Drivers**: show live understanding across a hard language (Punjabi) and a Canadian official language (French).
- **Constraints**: four weeks; team speakers available for both languages.

## Decision

Build: (1) language picker, (2) consent in the patient's language, (3) live tone-aware interpretation on the TV with empathy nudge, (4) dose read-back, (5) explain-back check, (6) off-the-record pause and human interpreter button (mocked), (7) transcript review with amendments, (8) note with provenance tags and Punjabi summary read aloud, (9) record-verified badge with tamper demo. Out of scope: login, database, quality tiers, data residency, communication coaching, real interpreter integration, live use of the other ten languages.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Full roadmap change | Complete vision | 47 tasks, cannot finish in four weeks | Too large |
| Interpretation only | Smallest | Loses the verified record and trust story | Undersells the product |

## Consequences

- **Positive**: achievable, memorable demo.
- **Negative**: demo shortcuts (mocked interpreter, in-memory state) must not leak into the product.
- **Risks and mitigations**: shortcuts are recorded as TDMs or demo-scoped IDRs.

## Implementation

OpenSpec change `demo-night-mvp`, capability `demo-consultation-flow`.

## Review Notes

- 2026-10-22, rashodkorala: Accepted by the project lead in the planning conversation.
