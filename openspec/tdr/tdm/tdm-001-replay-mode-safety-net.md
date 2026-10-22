---
id: tdm-001
title: "Replay mode and backup video as demo safety net"
status: proposed
date: 2026-10-22
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: temporary
related_decisions: [mdd-003, cdr-001]
related_specs: []
related_changes: [demo-night-mvp]
expires: 2026-11-20
ai_context:
  implementation_priorities:
    - "Replay a recorded CDR-001 event log through the same screens"
  framework_hints:
    - "server replay endpoint reads a JSON event log"
  validation_rules:
    - "Replay mode is clearly toggled and never used silently"
affects: []
implementation_refs: []
test_refs: []
---

# TDM-001: Replay mode and backup video as demo safety net

## Summary

If the network or a service fails on demo night, replay a recorded session through the same screens, with a screen-recorded video as the last resort.

## Context

- **Situation**: venue wifi and live AI services are outside our control.
- **Why temporary**: only needed for demo night.
- **Review or expiry trigger**: expires 2026-11-20.

## Decision

Record a full rehearsal's CDR-001 event log and audio; add a server replay mode that emits it at the original pace; record a backup video at the final rehearsal.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| No fallback | Less work | Demo fails if wifi fails | Too risky |

## Consequences

- **Positive**: the demo survives outages.
- **Negative**: small extra build.
- **Risks and mitigations**: test replay with the network disconnected.

## Implementation

`server/replay.py`; recorded logs in `server/replays/`.

## Review Notes

- 2026-10-22, Claude (agent): Drafted as a proposal. Awaiting human review; do not implement until accepted.
