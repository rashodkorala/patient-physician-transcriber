# Design

## Context

See proposal.md for motivation.
Today one Claude call (`translate` in `server/graph/turn_graph.py`, per ADR-004 and ADR-006) reads the speaker's emotion and certainty and writes a first-person translation plus a back-translation.
The `verify` node runs the critical value check and a tone check that compares the original with that back-translation.
The browser speaks the translation itself through the Azure SDK (`web/lib/speech.ts`, per ADR-005), driven by `web/components/Controller.tsx`.
Visits hold no names, and state is in memory only (ADR-007).

## Goals / Non-Goals

**Goals:**

- Reported-speech relays without weakening any existing safety check.
- The server is the only place that decides what may be spoken.
- Names add no step to a visit when a default is saved.

**Non-Goals:**

- Changing the turn graph's shape, retry rules, or outcome order.
- Persisting names server-side across visits.

## Decisions

### 1. Reported speech is a prompt change inside the existing translate node (per MDD-004, ADR-004)

The translate instructions gain the mediator rules: name the speaker, third person, plain wording, exact critical values, no own advice.
The turn input gains `<speaker_name>` and `<listener_name>` tags, filled from visit state or the fallbacks.
The back-translation is asked for in the same reported form, so the tone check compares like with like.
Alternative: a separate rewrite step after a first-person translation.
Rejected because it adds a model call to every turn and a second place where meaning can drift.

### 2. The tone check is told the frame is expected (per MDD-004, ADR-006)

The tone check instructions state that "X is saying" and the change to third person are expected, and that only meaning, certainty, and warmth count.
Critical value checks need no change: they compare values, and the frame adds none.
A frame that contains a number (for example a name with a digit) is not expected; names are validated as text without digits.

### 3. Names live in visit state; the default lives on the controller device (per CDR-003, ADR-007)

`visit.set_names` sets either name at any time, and the change applies from the next turn.
The saved default physician name is kept in the controller's browser storage and sent with `visit.set_names` when a visit opens.
Alternative: a server config default.
Rejected because each physician on a shared clinic machine may differ, and the controller is where they set it.

### 4. The introduction is a small server-side flow (per CDR-003)

`visit.start_introduction` moves the visit through `asking_physician`, `asking_patient`, and `done`, skipping known names.
Each step emits an `interpreter.line` with fixed, pre-reviewed text per language from the i18n content, not model-written text.
A spoken reply goes through recognition as a normal push-to-talk, then a small name extraction call (the Haiku model already used for the tone check, per ADR-006) proposes a name, which the controller confirms.
Fixed lines are used because the introduction must be reviewed by native speakers like the rest of the knowledge base (ADR-002).

### 5. Server-side synthesis with speak-by-id (per ADR-009, CDR-003)

`GET /api/speech/{id}` looks up the id: a settled final turn, a confirmed read-back turn, or an interpreter line.
Anything else returns 404, which enforces the interpreter-voice spec on the server, not in the browser.
The server calls OpenAI `gpt-4o-mini-tts` with streaming output and an `instructions` string built from `emotion` and `certainty` (for example worried with high certainty: "Calm, gentle, and serious; speak clearly and not too fast").
The mapping is a small fixed table in code, reviewed with the tone guides, not model-written.
One voice is chosen per visit language pair and kept for the whole visit.
`web/lib/speech.ts` keeps `speak(...)` and plays the streamed audio, with the Azure synthesizer kept behind it as the fallback.

### 6. Latency (per ADR-009, EDR-002)

The reported frame adds a few words to each relay.
Streaming audio lets speech start before synthesis finishes; speech start is logged in the existing latency CSV.
The target stays a median under 3 seconds from release to audio, as in demo-night-mvp task 1.7.

## Risks / Trade-offs

- [Punjabi voice quality may be worse than Azure's] → the listening test in task group 0 decides; Azure stays as the fallback per language.
- [Third person can confuse "he", "she", and "you"] → names are used rather than pronouns where possible, and the native speakers review sample relays.
- [Longer relays slow the visit] → latency is measured per turn; the frame is kept short ("Dr. Thomas says ...").
- [A misheard name is repeated all visit] → names are confirmed before use and editable at any time.
- [Server audio adds a hop] → streaming; measured against the Azure baseline.
- [Decisions scoped to demo-night-mvp] → group 0 asks the project lead to extend their `related_changes` before any code.

## Migration Plan

Built after demo night on a branch from the demo build.
The demo-night behaviour stays available until this change is accepted end to end; rollback is reverting the prompt and switching `speak()` back to Azure.

## Open Questions

- Which OpenAI voice per language pair; decided by the listening test in task 0.4, without changing the design.
- Exact interpreter line wording per language; written with the native speakers in task 2.4.
