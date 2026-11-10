---
id: tdm-005
title: "Hidden record-tamper control for the demo"
status: accepted
date: 2026-11-09
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: temporary
related_decisions: [mdd-003, idr-003, cdr-001, cdr-006, tdm-002]
related_specs: [demo-consultation-flow]
related_changes: [demo-night-mvp]
expires: 2026-11-30
ai_context:
  implementation_priorities:
    - "One controller command, demo.tamper_record, alters one stored turn or amendment entry once per visit, without rehashing, so the normal verification turns the badge broken"
    - "The shared and review screens learn of it only through record.integrity; the controller and record view mark it"
    - "Remove the command, its handler, its event, its controller UI, and its tests by the expiry date"
  framework_hints:
    - "Reuse HashChain.tamper in server/hash_chain.py (IDR-003); the command is defined in CDR-006"
    - "demo.tamper_record joins CONTROLLER_COMMANDS; demo.tamper_state joins CONTROLLER_ONLY_EVENTS"
  validation_rules:
    - "Accepted only from the controller connection, which is the presenter; there is no separate presenter-mode switch"
    - "Fires at most once per visit; a second command is refused"
    - "Never carried into add-multilingual-medical-consultation or any product build"
    - "Detection always comes from the normal IDR-003 verification, never from the control setting the badge"
affects: [server/main.py, server/visit_store.py, server/contracts.py, web/components/Controller.tsx]
implementation_refs: []
test_refs: []
---

# TDM-005: Hidden record-tamper control for the demo

> Technical Decision Memo. Only a human may set `status: accepted`.

## Summary

For demo night only, a hidden controller control alters one stored transcript entry once per visit, without rehashing it, so the audience sees the record verified badge turn broken and name the altered turn (beat 9, task 3.8).
It is removed after demo night and never ships in the product.

## Context

- **Situation**: IDR-003 accepts "a hidden demo control alters one stored segment to show detection", and CDR-006 gives it a channel command, `demo.tamper_record`.
  Like the mismatch injection (TDM-002), it deliberately breaks a safety property so the audience can see the safeguard catch it.
- **Why temporary**: a control that edits the clinical record has no place in a product, even when the edit is detected.
- **Review or expiry trigger**: expires 2026-11-30, after demo night on 19 November 2026; reviewed earlier if demo night moves or the control misbehaves in rehearsal.

## Decision

1. **Scope.**
   - Presenter only: the command is accepted only from the controller connection, which is the presenter; screen and review connections' copies are dropped.
   - Once per visit: after it fires, any further `demo.tamper_record` is refused for that visit.
   - Targets: one existing `turn` or `amendment` chain entry (CDR-006); consent, confirmation, explain-back, interpreter, and summary entries cannot be targeted.
   - Effect: the entry's stored text is changed in place and its hash is not recomputed; the server then runs the normal IDR-003 verification and publishes `record.integrity` with `status: broken` and `brokenAt` set to the altered entry's id.
   - Never in production: only the `demo-night-mvp` change may use it, and no product build or roadmap change may carry it.
2. **Visibility.**
   - The controller and the `/record` view (controller role, CDR-007) mark the altered entry as changed by the tamper control, from the controller-only `demo.tamper_state` event and `visit.state.tamper`.
   - The TV and the review screen show only the broken badge and the named turn, never a tamper label, live or through `visit.state`.
3. **Removal conditions.**
   - On or before 2026-11-30, the command, its handler, `demo.tamper_state`, `visit.state.tamper`, the controller control, and their tests are deleted, and CDR-006 is amended or superseded to drop them; `HashChain.tamper` may stay as a test helper.
   - It is removed sooner if a rehearsal shows it can fire by accident, if demo night is cancelled, or if the project lead withdraws it.
   - Renewal needs a new human decision recorded in this memo before the expiry date; `scripts/check_tdr.py` flags it once expired.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Cover the control under TDM-002 | One memo for both demo controls | Different behaviour, risk, and removal list; TDM-002 expires on 2026-11-20 | Its own memo, as the decision owner chose |
| No tamper control, describe detection only | Nothing to remove | The audience never sees the badge break | Beat 9 needs a live break |
| Tamper through a debug HTTP endpoint | No channel change | A second path to the record that bypasses the role filter; easier to leave running | One controller command on the visit channel |
| Tamper by deleting an entry | Also detected | The badge would name the next entry, not the altered turn | Altering text names the turn itself |
| Allow several tampers per visit | Repeatable on stage | More ways to confuse the record view; a rehearsal can start a new visit instead | Once per visit |

## Consequences

- **Positive**: the integrity story is shown live, with detection coming from the real verification code.
- **Negative**: a deliberate record-altering control exists in the demo build until it is removed.
- **Risks and mitigations**: accidental firing on stage, mitigated by the folded presenter section on the controller, once per visit, and rehearsal; leakage into the product, mitigated by the expiry, the removal list, and the scope binding only `demo-night-mvp`.

## Implementation

Built with demo-night-mvp task 3.8 under CDR-006 and IDR-003, after this memo and CDR-006 are accepted.
Code carries `@implements TDM-005: Hidden record-tamper control for the demo`.
Tests: the command is dropped from screen and review connections; it alters a turn and `record.integrity` names that turn's `segmentId`; a second command in the same visit is refused; consent and summary entries cannot be targeted; no screen or review connection receives `demo.tamper_state` or a tamper label, live or through `visit.state`.

## Review Notes

- 2026-11-09, Claude (agent): Drafted as a proposal for the supervising session, at rashodkorala's direction (relayed by the supervising session) that the tamper control gets its own memo with an expiry. Awaiting human review; do not implement until accepted.
- 2026-11-09, rashodkorala: Accepted ("accept TDM-005 and record it"). Recorded by Claude (agent) at rashodkorala's explicit request.
