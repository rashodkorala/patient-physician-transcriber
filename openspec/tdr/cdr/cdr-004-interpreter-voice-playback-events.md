---
id: cdr-004
title: "Interpreter voice playback on the visit channel"
status: accepted
date: 2026-11-06
authors: ["Claude (agent)"]
reviewers: []
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: contract
related_decisions: [cdr-001, cdr-003, adr-001, adr-007, adr-010]
related_specs: [shared-screen-presence]
related_changes: [orb-speaking-state, trust-across-the-barrier]
ai_context:
  implementation_priorities:
    - "Additive to CDR-001: two new controller commands, one new public event, and one new optional visit.state field; no existing message changes shape"
    - "The server is the single source of the speaking state; screens only display it"
    - "The speaking state can never stick: it clears on voice.ended, on controller disconnect, and after a 60 second ceiling"
  framework_hints:
    - "Pydantic models in server/contracts.py; TypeScript in web/lib/contracts.ts; regenerate web/lib/generated/"
    - "Add both commands to CONTROLLER_COMMANDS so screens' copies are dropped like every other controller command"
    - "Reuse the speak gate that already decides GET /api/speech/{id} (CDR-003), so an id that may not be spoken can never show as speaking"
  validation_rules:
    - "voice.started is accepted only for an id the speak gate allows, in the language that id would be spoken in"
    - "voice.ended clears the state only when its speechId and language match the current speech; any other end is ignored without an event"
    - "voice.speaking carries no text, tone, emotion, or certainty"
affects: [server/contracts.py, server/main.py, server/visit_store.py, web/lib/contracts.ts, web/lib/generated/, web/components/SharedScreen.tsx]
implementation_refs: []
test_refs: []
---

# CDR-004: Interpreter voice playback on the visit channel

## Summary

Lets the controller tell the server when the interpreter's voice starts and stops, and lets the server tell every screen, so the shared screen can show that the interpreter is speaking.
Additive to CDR-001, in the same way as CDR-003.

## Context

- **Technical drivers**: the shared screen's orb has Ready, Listening, and Translating states, all driven by existing events.
  A Speaking state needs to know when audio is actually playing.
- **Constraints**: the interpreter's voice is played only by the controller browser on the physician's laptop (CDR-003 speak-by-id, ADR-010 voice, Azure fallback per ADR-005).
  The shared screen is a separate browser on the TV that only receives the visit WebSocket (ADR-001), so a signal inside the controller page cannot reach it.
  The server cannot see playback either: the Azure fallback never touches the server, and a finished audio stream is not the end of playback, because the browser buffers it.
- **Related**: the continuous-listening change adds a speaking signal inside the controller page; this contract is how that signal leaves the page.
  Its decision record is accepted on that change's branch and is not on the main branch yet, so it is cited here by change name; add its id to `related_decisions` once it merges.

## Decision

The controller reports playback start and end for each speech id, the server checks each report against the speak gate and keeps one speaking state on the visit, and the server publishes that state to every role.

## Contract Specification

Commands (client to server):

| Command | Sender |
|---|---|
| `voice.started` (`speechId`, `language`) | Controller only; when audio for that id and language begins to play |
| `voice.ended` (`speechId`, `language`) | Controller only; when that audio finishes, fails, or is stopped |

Events (server to clients):

| Event | When |
|---|---|
| `voice.speaking` (`speaking`, `speechId`, `language`) | The speaking state changed; every role |

`visit.state` gains an optional `speaking` field for every role, holding the same `VoiceSpeaking` value, so a screen that connects mid-speech shows the right state.

Server rules:

1. **Controller only.** Both commands join `CONTROLLER_COMMANDS`; a screen's copy is dropped silently, as for every other controller command.
2. **Only what may be spoken.** `voice.started` is accepted only if the speak gate allows the id (a settled `final` turn, a confirmed read-back turn, or an `interpreter.line`) and `language` is the language that id is spoken in: the turn's target language, or one of the line's languages.
   Anything else returns an `error` to the sender and publishes nothing.
   This covers both voices, because the gate decides what may be spoken whichever voice says it.
3. **One voice at a time.** A valid `voice.started` replaces any current speech and publishes `voice.speaking` with `speaking: true`.
   A repeat for the speech already playing publishes nothing.
4. **Matched ends only.** `voice.ended` clears the state and publishes `speaking: false` only when its `speechId` and `language` match the current speech.
   A stale or unknown end is ignored without an error, because the controller's queue can finish a speech after a newer one started.
5. **Never stuck.**
   - When the controller connection that started the current speech disconnects, the server clears the state and publishes `speaking: false`.
   - When no `voice.ended` arrives within 60 seconds of `voice.started`, the server clears the state and publishes `speaking: false`.
     The longest interpreter line is well under this.
   - The state is a field of the in-memory visit (ADR-007), so a new visit starts silent.
6. **No content.** `voice.speaking` carries only the id, the language, and the flag.
   Turn ids and line ids are already public through `turn.result` and `interpreter.line`, so nothing private reaches the screen.

## Data Schemas

- `VoicePlayback` (both commands): `{ speechId: string, language: Language }`, where `speechId` is 1 to 64 characters.
- `VoiceSpeaking` (event and `visit.state.speaking`): `{ speaking: boolean, speechId: string | null, language: Language | null }`.
  `speechId` and `language` are non-null exactly when `speaking` is true.

## Evolution Strategy

Additive to CDR-001: existing events keep their shape, and `visit.state.speaking` is optional, so older screens ignore it, and older screens also ignore the unknown event type.
If a later screen ever plays audio itself, it can send the same commands once it is allowed to; the event does not change.

## Testing Requirements

Contract tests in pytest and `npm run check:contracts` cover both commands, the event, and the new `visit.state` field.
Channel tests cover:
- a screen sending either command, with no effect;
- `voice.started` refused for blocked, escalated, rejected, unsettled, and unknown ids, and for a wrong language;
- the event reaching every role;
- a repeated start publishing nothing;
- a stale end ignored;
- controller disconnect clearing the state;
- the 60 second ceiling clearing it, with an injectable clock;
- `visit.state` reporting the state to a screen that connects mid-speech.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Server infers playback from `GET /api/speech/{id}` | No new commands | Misses the Azure fallback, which never calls the server; stream end is not playback end, because the browser buffers | Wrong exactly when the voice falls back or audio is long |
| Screen estimates speaking time after `turn.result` | No contract change | Shows Speaking when the voice failed or is queued behind another line; no interpreter lines | Can show something untrue on the shared screen |
| One boolean command with no id | Smallest message | Cannot tell a stale end from the current one when the controller queues speeches | Ends from the queue would clear the wrong speech |
| A `speaking` stage in `turn.status` | Reuses an event | Interpreter lines are not turns; mixes playback into the turn lifecycle that settles before audio starts | Does not cover the introduction or name questions |

## Consequences

- **Positive**: the shared screen shows when the interpreter is speaking, for relays and for the interpreter's own lines, from one server-held state.
- **Negative**: two more commands and a small timer on the server; the controller must report ends on every path, including failures.
- **Risks and mitigations**: a lost end would leave the orb in Speaking, mitigated by the disconnect reset and the 60 second ceiling.

## Implementation

The `orb-speaking-state` change.
The server and the shared screen are built by the orb work.
The controller side (sending the commands from the speaking signal) is built by the continuous-listening work, which owns `web/lib/speech.ts` and `web/components/Controller.tsx`.

## Review Notes

- 2026-11-06, Claude (agent): Drafted as a proposal for the `orb-speaking-state` change at rashodkorala's direction to add a voice speaking event to the channel (relayed by the supervising session). Awaiting human review; do not implement until accepted.
- 2026-11-06, rashodkorala: Accepted. Recorded by Claude (agent) at rashodkorala's explicit request.
- 2026-11-10, rashodkorala: Extended to the trust-across-the-barrier change under the blanket authorisation given in session (see MDD-005). Recorded by Claude (agent) at rashodkorala's explicit request.
