---
id: adr-007
title: "In-memory visit state with WebSocket updates; no database for the demo"
status: proposed
date: 2026-10-22
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: architecture
related_decisions: [adr-001, mdd-003]
related_specs: []
related_changes: [demo-night-mvp]
ai_context:
  implementation_priorities:
    - "One active visit at a time held in server memory"
    - "Push every change to all screens"
  framework_hints:
    - "FastAPI WebSocket endpoint; events per CDR-001"
  validation_rules:
    - "Restarting the server clears the visit; acceptable for demo only"
affects: [server/visit_store.py, server/main.py]
implementation_refs: []
test_refs: []
---

# ADR-007: In-memory visit state with WebSocket updates; no database for the demo

## Summary

Hold the demo visit in server memory and push updates to all screens over a WebSocket; no database.

## Context

- **Technical drivers**: TV, laptop, and phone must stay in sync instantly.
- **Quality attributes**: simplicity, reliability on the night.
- **Constraints**: demo only; no persistence requirement.

## Decision

`server/visit_store.py` holds the visit; `server/main.py` broadcasts CDR-001 events to every connected screen.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Postgres or SQLite | Persistent | Setup time with no demo value | Deferred to product |
| Polling REST | Simpler client | Laggy captions | Worse demo |

## Consequences

- **Positive**: fast, simple.
- **Negative**: no persistence.
- **Risks and mitigations**: replay mode (TDM-001) covers failures.

## Implementation

`server/visit_store.py`, WebSocket route in `server/main.py`.

## Review Notes

- 2026-10-22, Claude (agent): Drafted as a proposal. Awaiting human review; do not implement until accepted.
