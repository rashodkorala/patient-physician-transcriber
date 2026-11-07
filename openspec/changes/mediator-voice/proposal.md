# Proposal

## Why

The interpreter repeats each speaker's words in their own voice, and the synthesised voice sounds robotic.
The product should feel like a real interpreter sitting between the physician and the patient: one who greets them, knows their names, relays what each said in a warm and human way, and sounds like a person (MDD-004).

## What Changes

- Each turn is relayed in reported speech that names the speaker, in both directions, for example "Dr. Thomas is saying you should take this medicine 2 times a day after every meal".
- Wording may be plain and everyday, but numbers, doses, units, frequencies, dates, and medication names stay exact, and no instruction is softened, added, or dropped.
- The tone check accepts the reporting frame as expected, so it does not escalate turns for it.
- A visit opens with a spoken introduction by the interpreter in both languages.
  It asks for the physician's name, then the patient's name, skipping any name already known.
- A physician or clinic can save a default physician name once, so that question is skipped in every visit.
- Spoken output moves to a more natural voice whose delivery follows the speaker's emotion and certainty (ADR-009).
  Recognition is unchanged.
- The server decides what may be spoken: only a turn that passed its checks, or an interpreter line, can be synthesised.
- The shared screen shows the reported-speech translation as the caption; the original stays alongside it.

## Out of scope

- Changing the demo-night build or its nine-beat script (MDD-003); this change starts after demo night.
- User accounts, clinic administration, or storing names beyond the visit and the device's saved default.
- A live speech-to-speech voice agent (rejected in ADR-009).
- Companion speakers' names; companions are relayed as "the patient's companion".

## Capabilities

### New Capabilities

- `mediator-interpretation`: how the interpreter relays each turn as a person between the parties, in reported speech, with critical values kept exact.
- `visit-introduction`: the interpreter's spoken opening, name collection, and the saved default physician name.
- `interpreter-voice`: how and when the interpreter's words are spoken aloud, including expressive delivery and the speak-only-checked rule.

### Modified Capabilities

None. `openspec/specs/` has no main specs yet; the demo-night behaviour lives in the unarchived `demo-night-mvp` change, which this change does not modify.

## Decisions relied on

- Proposed, need human review (task group 0): MDD-004 (mediator voice), ADR-009 (voice output), CDR-003 (participant names and interpreter lines on the visit channel).
- Accepted, but scoped only to `demo-night-mvp`; a human must add `mediator-voice` to their `related_changes` before they bind this change: ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007, CDR-001, CDR-002, EDR-002, IDR-001.
- Accepted and already binding: MDD-001, MDD-002, EDR-001.

## Impact

- `server/graph/turn_graph.py`: translation and tone check instructions; names passed into each turn.
- `server/contracts.py`, `web/lib/contracts.ts`, `web/lib/generated/`: names and interpreter lines on the visit channel (CDR-003).
- `server/main.py`: name commands, the introduction flow, and a speech endpoint.
- `web/lib/speech.ts`, `web/components/Controller.tsx`, `web/app/screen/page.tsx`: playback of server audio, the name step, and the saved default.
- New dependency: OpenAI API on the server (key already held per ADR-005).
- Tests: turn graph, contracts, introduction flow, and speech gating.
