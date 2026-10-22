---
id: cdr-001
title: "Visit WebSocket event contract"
status: accepted
date: 2026-10-22
authors: ["Claude (agent)"]
reviewers: ["rashodkorala", "front-end owner", "back-end owner"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: api-contract
related_decisions: [adr-001, adr-007]
related_specs: []
related_changes: [demo-night-mvp]
ai_context:
  implementation_priorities:
    - "Single WebSocket per screen"
    - "Server is the source of truth for visit state"
  framework_hints:
    - "FastAPI WebSocket on the server; native WebSocket in Next.js client"
    - "Shared event names in server/contracts.py and web/lib/contracts.ts"
  validation_rules:
    - "Every event has type, visitId, seq, ts, payload"
    - "empathy.nudge never reaches /screen or /review"
affects: [server/main.py, web/lib/socket.ts]
implementation_refs: []
test_refs: []
---

# CDR-001: Visit WebSocket event contract

## Summary

Defines the events and commands exchanged between the server and the controller, TV screen, and review screens over a WebSocket.

## Context

- **Integration point**: server (ADR-001) to Next.js screens.
- **Related decisions**: ADR-001, ADR-007.
- **Requirements**: live captions, status updates, private nudges, review actions.

## Decision

Adopt the event and command set below as version 1 of the visit channel.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Server-sent events plus REST | Simple one-way stream | Commands need a second channel | WebSocket is simpler overall |
| Shared database polling | No socket | Latency | Bad for live captions |

## Contract Specification

Channel: `ws://<server>/ws/visit` (one visit at a time). Server to clients broadcasts every event; clients send commands.

| Event (server to clients) | When |
|---|---|
| `visit.state` | On connect: full current state |
| `turn.started` | A speaker pressed push-to-talk |
| `turn.status` | Each graph node starts (`analysing`, `checking_glossary`, `translating`, `verifying`, `retrying`) |
| `turn.result` | Final translation for a turn (CDR-002 payload) |
| `turn.readback_required` | Critical values need speaker confirmation before speaking |
| `empathy.nudge` | Private suggestion for the physician controller only |
| `visit.paused` / `visit.resumed` | Off-the-record toggled |
| `interpreter.escalation` | Human interpreter offered or requested |
| `segment.amended` | A segment was confirmed or corrected in review |
| `record.integrity` | Hash chain status (`verified` or `broken`) |

| Command (client to server) | Sender |
|---|---|
| `turn.submit` (speaker, language, recognised text, recognition confidence) | Controller |
| `turn.readback_confirm` / `turn.readback_reject` | Controller |
| `visit.pause` / `visit.resume` | Any screen |
| `interpreter.request` | Any screen |
| `segment.confirm` / `segment.amend` | Review screen |

## Data Schemas

Every message: `{ "type": string, "visitId": string, "seq": integer, "ts": ISO-8601 string, "payload": object }`. `seq` increases by one per server event so clients can detect gaps and request `visit.state`.

- `turn.started.payload`: `{ turnId, speaker: "patient"|"physician"|"companion", language: BCP-47 }`
- `turn.status.payload`: `{ turnId, stage: string }`
- `turn.result.payload`: CDR-002 `TurnResult`
- `empathy.nudge.payload`: `{ turnId, emotion, suggestion, phrase, phraseLanguage }` (sent only to controller connections)
- `interpreter.escalation.payload`: `{ reason: "low_confidence"|"high_risk"|"requested", turnId?: string }`
- `segment.amended.payload`: `{ segmentId, by: "patient"|"physician", action: "confirm"|"amend", newText?: string }`
- `record.integrity.payload`: `{ status: "verified"|"broken", headHash, brokenAt?: segmentId }`

## Evolution Strategy

Version in the URL path once a second version exists (`/ws/v2/visit`). Additive fields are non-breaking; renaming or removing a field needs a new CDR that supersedes this one.

## Testing Requirements

Server contract tests assert each event shape; a front-end test replays a recorded event log and checks the screens render; a test asserts `empathy.nudge` is only sent to controller connections.

## Consequences

- **Positive**: one clear contract for parallel front-end and back-end work.
- **Negative**: changes need review.
- **Risks and mitigations**: replay mode (TDM-001) reuses recorded event logs.

## Implementation

Code carries `@contract ws:/ws/visit` and `@implements CDR-001: Visit WebSocket event contract`.

## Review Notes

- 2026-10-22, Claude (agent): Drafted as a proposal. Awaiting human review; do not implement until accepted.
- 2026-10-22, rashodkorala: Accepted in decision review. Recorded by Claude (agent) at rashodkorala's explicit request.
