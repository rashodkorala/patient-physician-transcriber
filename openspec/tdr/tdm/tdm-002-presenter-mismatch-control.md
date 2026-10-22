---
id: tdm-002
title: "Presenter mismatch control for the blocked-dose beat"
status: accepted
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
    - "Arm once; fire on the next physician turn that contains a critical value; multiply its first dose number by 10 on both attempts so the normal rules block it"
    - "The presenter can cancel an armed injection before it fires"
  framework_hints:
    - "Presenter-only commands demo.inject_mismatch and demo.cancel_injection on the controller connection; controller-only event demo.injection_state (CDR-001)"
  validation_rules:
    - "Never available outside presenter mode"
    - "Injection state and labels never reach /screen or /review, live or via visit.state"
    - "The injection is marked on the controller and in the record or note view only; the review screen shows the turn as blocked, then repeated, with no wrong translation"
    - "Blocking still comes from the normal verify node, not from the control"
affects: []
implementation_refs: []
test_refs: []
---

# TDM-002: Presenter mismatch control for the blocked-dose beat

## Summary

For demo night only, a presenter-only control makes the next physician turn that contains a critical value have its first dose number multiplied by 10 in the translation, on both attempts, so the audience sees a dose blocked, the speaker asked to repeat, and the repeat confirmed.

## Context

- **Situation**: the blocked-dose rule (CDR-002) is the strongest safety story, but a real mismatch cannot be relied on to happen on stage.
- **Why temporary**: a fault-injection control has no place in the product.
- **Review or expiry trigger**: expires 2026-11-20.

## Decision

Add presenter-only commands `demo.inject_mismatch` and `demo.cancel_injection` (controller connection, presenter mode only) and a controller-only event `demo.injection_state` (`armed | fired | cancelled`) to CDR-001 as an additive change.

1. **What changes:** the first dose number in the translation is multiplied by 10 (for example 0.4 mg becomes 4 mg), a realistic and dangerous slip.
2. **When it fires:** once armed, on the next physician turn that contains a critical value, on both attempts; turns without a critical value leave it armed. The presenter can cancel it before it fires. It fires at most once per arming.
3. **Blocking:** the verify node blocks the turn under the normal CDR-002 rules; the control never sets the status itself.
4. **Visibility:** the injection is marked on the physician's controller and in the record or note view only. The TV and the patient's review screen never show it, live or through `visit.state`. On review, the turn appears as "blocked, then repeated" with no wrong translation.

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

`server/graph/` honours a one-shot injection flag; the controller presenter panel sends `demo.inject_mismatch` and `demo.cancel_injection`. Tests: an armed flag waits through a turn without critical values; it fires on the next turn with one and multiplies the first dose number by 10; that turn is blocked on both attempts; the following turn is unaffected; cancel before firing leaves the next dose untouched; no screen or review connection receives injection state or labels, live or via `visit.state`; the review screen shows the turn as blocked, then repeated, without translation or injection label.

## Review Notes

- 2026-10-22, Claude (agent): Drafted as a proposal. Awaiting human review; do not implement until accepted.
- 2026-10-22, rashodkorala: Accepted with clarifications: the first dose number is multiplied by 10; fires on the next physician turn containing a critical value and can be cancelled; injection visible on the controller and record view only, never on the TV or review screen. Recorded by Claude (agent) at rashodkorala's explicit request.
