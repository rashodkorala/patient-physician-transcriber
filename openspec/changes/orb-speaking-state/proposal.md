# Proposal

## Why

The shared screen's orb shows when the interpreter is ready, listening, or translating, but not when it is speaking.
In the room, that is the moment both people most need to know whose turn it is: while the interpreter speaks, nobody should start talking.
The voice plays on the physician's laptop and the orb is on the TV, a separate screen, so the screen needs to be told.

## What Changes

- While the interpreter's voice is playing, the shared screen shows a Speaking state: the orb in both speakers' colours with rings moving out from it.
- It covers relays of a turn and the interpreter's own lines, such as the introduction and the name questions.
- Speaking is shown only for words that passed their checks, and only while audio is actually playing.
- If the physician's laptop drops off or a playback end is lost, the screen leaves Speaking within a minute at most.
- A screen that is opened or reconnects while the interpreter is speaking shows Speaking straight away.

## Out of scope

- Any change to what is spoken, when it is spoken, or how it sounds (CDR-003, ADR-010).
- A voice level or waveform on the screen; the orb shows that speech is playing, not how loud it is.
- Hands-free listening and its pause while the interpreter speaks (the continuous-listening change), apart from sharing the same speaking signal.
- An orb on the physician controller.

## Capabilities

### New Capabilities

- `shared-screen-presence`: how the shared screen shows what the interpreter is doing right now (ready, listening, translating, speaking).

### Modified Capabilities

None. `openspec/specs/` has no main specs yet.

## Decisions relied on

- Proposed, need human review (task group 0): CDR-004 (interpreter voice playback on the visit channel).
- Accepted: ADR-001 (shared TV screen client), ADR-007 (in-memory visit state), CDR-001 (visit WebSocket events), CDR-003 (speak-by-id and interpreter lines), EDR-002 (testing).
  A human must add `orb-speaking-state` to their `related_changes` before they bind this change.
- Accepted and already binding: MDD-001, MDD-002, EDR-001.
- Accepted on the continuous-listening branch, not yet on the main branch: that change's decision record for the controller's speaking signal; cite it by id here once it merges.

## Impact

- `server/contracts.py`, `web/lib/contracts.ts`, `web/lib/generated/`: the two commands, the event, and the `visit.state` field (CDR-004).
- `server/main.py`, `server/visit_store.py`: the handlers, the speak-gate check, the disconnect reset, and the 60 second ceiling.
- `web/components/SharedScreen.tsx`, `web/components/Orb.tsx`, `web/components/orb.module.css`: the Speaking state.
- `web/lib/speech.ts`, `web/components/Controller.tsx`: sending the commands from the speaking signal, built by the continuous-listening work, which owns these files.
- Tests: contract and channel tests in pytest, `npm run check:contracts`, and an e2e script for the screen.
