# Design

## Context

Motivation and scope: `proposal.md` and MDD-005.
Behaviour: `specs/*/spec.md`.
Every technical choice cites its record in `openspec/tdr/`.

Constraints: the demo-night build must keep working (every existing end-to-end script passes); manner is read from text only; nothing is spoken without the speak gate; no model call is added to the turn's critical path.

## Goals / Non-Goals

**Goals:**
- The patient can act during the visit without permission or English.
- The physician's manner is audible in the voice and readable in the patient's language.
- The physician learns, privately and in the moment, how the visit is landing.
- One design system on every screen that a clinic can put on a wall.

**Non-Goals:**
- Prosody, persistence, privacy, accounts, or a real interpreter connection.

## Decisions

### Channel (CDR-008)

```
 [TV /screen]    [Laptop /control]    [Tablet /patient (review role)]   [Phone /record]
      |                 |                        |                           |
      +---- patient.signal, interpreter.line, turn.result (+manner), visit.state (+signals) ----+
                        |
                        +---- controller only: trust.update, visit.state.trust, turn.analysis (+manner)
                        |
                 server/main.py: signal handler (2 s hold per connection, chain entry of kind signal,
                 interpreter line in the physician's language), ask_if_clear handler, companion turns
```

### Manner (IDR-005)

The translate call's `Draft` gains `manner`; the prompt defines the eight values and says `plain` is the default.
The frame rule and the tone-check wording are in IDR-005.
`to_caption` sets `manner` for a final physician turn only.
`voice.py` gains `MANNER_DELIVERY` and `delivery_for_turn(speaker, manner, emotion, certainty)`: physician turns by manner, others by emotion (conveying), with the existing certainty steadiness.
The speak gate uses `delivery_for_turn`.

### Trust advisor (ADR-002, ADR-006, MDD-005)

`server/trust.py` replaces `server/empathy.py`.
One background call per settled final turn on the tone model (Haiku 5.5, ADR-006), never on the turn's critical path:

- patient or companion turn: the empathy nudge as today (emotion in the nudge set), plus the deterministic `reassuranceLanded` (CDR-008 rule) computed by code from the visit's turn history;
- physician turn: a `culture` cue only when the retrieved tone and culture guidance for the patient language marks the topic sensitive; the model returns `null` otherwise.

Cues are English, at most 200 characters, controller only, never chained, never sent to the note or summary chains (ADR-011 already forbids private fields in their snapshots).
The trust timeline lives on the in-memory visit (ADR-007) and is sent in the controller's `visit.state.trust`.

### Patient signals

`patient.signal` is accepted from the review role only.
The server chains a `signal` entry (CDR-006, IDR-003), publishes `patient.signal` to every role, publishes a `trust.update` to controllers, and for `not_understood` and `slower` says a fixed interpreter line in the physician's language from `kb/content/interpreter/*.yaml` (CDR-003), naming the patient when known.
`repeat` is client side: the controller replays the last spoken translation in the patient's language by id through the existing speech endpoint.
Pause and the interpreter request reuse `visit.pause`, `visit.resume`, and `interpreter.request`, which any screen may already send (CDR-001).

### Companion turns (IDR-001, MDD-004)

The controller gets a third push-to-talk control, Companion, that submits in the patient's language.
Hands-free never labels a companion (IDR-004); the physician uses the Companion control for them.
The turn graph already frames a companion as "the patient's companion"; the note already allows `companion_stated` (ADR-011).

### Closing check (CDR-003)

`visit.ask_if_clear` says one interpreter line with two texts: the patient's language first (spoken), then the physician's.
Fixed text with the patient's name when known.

### Edge cases

- The Anthropic client gets a 25 second timeout and two retries for live calls (ADR-006, ADR-004); a turn that still fails reaches `turn.status` `failed`, and every screen shows it as not spoken.
- A signal within two seconds of the previous one from the same connection is refused `busy`.
- `repeat` before any spoken translation is refused `invalid`; a 404 from the speech endpoint shows nothing.
- A companion turn in the physician's language is refused.
- `trust.update` is filtered from screen and review connections and from their snapshots exactly like `turn.analysis`.

### Interface (ADR-012)

Tokens in `web/app/globals.css`; the system in `web/design/README.md`.
Every module stylesheet is rewritten to tokens; data-testids are unchanged.
The patient device (`web/components/PatientScreen.tsx`) wraps the existing review content with the signal panel above it and the latest caption in the patient's language.
`/review` redirects to `/patient`.

## Risks / Trade-offs

- [Manner read from words only] → labelled as such in the design README and the stage script; conservative default `plain`.
- [Visual regression two weeks before demo night] → every end-to-end script runs against the new styles; screenshots at 1920, 1280, and 390 are reviewed.
- [Speaker review backlog grows] → every new label and line is `_reviewer: pending` and listed in tasks.

## Migration Plan

Not applicable; in-memory state, one branch.

## Open Questions

- Whether the manner adverb in the frame reads naturally in Punjabi and Tamil (speaker review).
- Whether the TV should offer a dark mode toggle for dim rooms, beyond the operating system preference.
