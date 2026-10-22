---
id: tdm-002
title: "Presenter mismatch control for the blocked-dose beat"
status: proposed
date: 2026-10-22
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: temporary
related_decisions: [mdd-003, adr-004, cdr-001, cdr-002]
related_specs: [demo-consultation-flow]
related_changes: [demo-night-mvp]
expires: 2026-11-20
ai_context:
  implementation_priorities:
    - "Force one critical value mismatch on the next physician turn, on both attempts, so the normal rules block it"
  framework_hints:
    - "Presenter-only command demo.inject_mismatch on the controller connection; the turn graph alters one critical value in the translation for that turn only"
  validation_rules:
    - "Never available outside presenter mode"
    - "Never sent to or shown on /screen or /review"
    - "The injection is recorded in the transcript as a demo injection"
    - "Blocking still comes from the normal verify node, not from the control"
affects: []
implementation_refs: []
test_refs: []
---

# TDM-002: Presenter mismatch control for the blocked-dose beat

## Summary

For demo night only, a presenter-only control forces the next physician turn's translation to alter one critical value on both attempts, so the audience sees a dose blocked, the speaker asked to repeat, and the repeat confirmed.

## Context

- **Situation**: the blocked-dose rule (CDR-002) is the strongest safety story, but a real mismatch cannot be relied on to happen on stage.
- **Why temporary**: a fault-injection control has no place in the product.
- **Review or expiry trigger**: expires 2026-11-20.

## Decision

Add a presenter-only command `demo.inject_mismatch` (controller connection, presenter mode only) to CDR-001 as an additive change once this record is accepted. When set, the turn graph alters one critical value in the translation of the next physician turn on both attempts; the verify node then blocks the turn under the normal CDR-002 rules. The injection is recorded in the transcript as a demo injection and is never visible on the shared or review screens.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Describe the rule only | No extra code | The audience never sees the safety behaviour | Weaker demo |
| Wait for a real mismatch | Authentic | May never happen on stage | Unreliable |
| Pre-recorded clip of a blocked turn | No live risk | Breaks the live flow | Kept as the backup video |

## Consequences

- **Positive**: the audience sees the safety rule work live.
- **Negative**: a test-only control inside the demo build.
- **Risks and mitigations**: presenter-mode gate, transcript record of the injection, and expiry after demo night.

## Implementation

`server/graph/` honours an injection flag for one turn; controller presenter panel sends `demo.inject_mismatch`. Tests: injected turn is blocked on both attempts, the next turn is unaffected, and no screen or review connection receives the injection.

## Review Notes

- 2026-10-22, Claude (agent): Drafted as a proposal. Awaiting human review; do not implement until accepted.
