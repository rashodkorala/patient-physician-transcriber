# Proposal

## Why

The interpreter already carries words safely: doses are checked by code, the record is verified, and the patient can correct their own turns afterwards.
What it does not yet carry is trust.
During the visit the patient has no control of their own; pause and the human interpreter button sit on the physician's laptop.
The physician's manner, the care in how something is said, is lost: the voice follows the speaker's emotion rather than how they meant it, and the caption labels the translation's register rather than the physician's delivery.
Nothing tells the physician whether a reassurance landed or a point was missed until the explain-back at the end.
A companion in the room, the commonest real-world case, has no way to speak.
Rashod's direction on 2026-11-10: help both parties build trust with each other, because tone and emotion are what translation loses first; fix any decision that stands in the way; and make the interface fit a clinic or public health organisation.

## What Changes

- **The patient has a voice.** A patient device (`/patient`, the review role) carries, during the visit and in the patient's language first, five controls: I did not understand, please slow down, say that again, pause, and a human interpreter.
  A signal reaches the shared screen in both languages, the physician through a spoken interpreter line, the record, and the controller.
- **The physician's manner is carried.** Every turn gets a `manner` read from the words said.
  For physician turns it drives the interpreter's voice, may enter the reporting frame as one adverb, and is shown as a label in the patient's language on every caption.
  Patient and companion captions carry no manner or emotion label; their affect reaches the physician through the voice and the controller, as today.
- **The physician sees how it is landing.** A private trust view on the controller: emotion turn by turn, whether a reassurance landed, every patient signal, and a culture cue when a topic is sensitive in the patient's culture.
- **A companion can speak.** A third speaker control on the controller, in the patient's language, labelled companion everywhere.
- **The interpreter closes the loop.** A controller control makes the interpreter ask the patient, in their language, whether anything should be explained again.
- **A clinic design system.** Light paper, one hyperlegible typeface, meaning-only colour, sentence case, 56 pixel targets on the patient's device, the same tokens on every screen including the TV (ADR-012).
  This replaces the black and crème system.
- **Edge cases hardened.** Model calls time out instead of hanging a turn; a failed turn is shown on every screen as not spoken; signal bursts are held; a replay request for something the speak gate no longer allows shows nothing.

## Capabilities

### New Capabilities

- `patient-voice`: the patient's own controls during the visit and how each signal is carried.
- `manner-in-relay`: how the manner of a turn is read, voiced, framed, and labelled.
- `trust-signals-for-the-physician`: the physician's private trust view.
- `companion-turns`: a companion as a labelled third speaker.
- `clinic-interface`: the observable interface rules every screen follows.

### Modified Capabilities

- `demo-consultation-flow` (in the unarchived `demo-night-mvp` change): the "Tone labels" requirement becomes "Manner labels"; "Off-the-record pause" and "Human interpreter offer" gain the patient's own control.
  Amended in place in that change's spec, since `openspec/specs/` has no main specs yet.

## Decisions (TDRs)

- New, accepted under rashodkorala's blanket authorisation of 2026-11-10 and open to review once built: MDD-005 (trust layer), ADR-012 (clinic design system), CDR-008 (channel additions), IDR-005 (manner vocabulary and voice delivery).
- Existing records extended to this change: ADR-001 to ADR-007, ADR-010, ADR-011, CDR-001 to CDR-007, EDR-002, IDR-001, IDR-003, IDR-004, MDD-004.
- Registry: `openspec/tdr/index.md`.

## Out of Scope

Prosody or audio emotion recognition; same-language transcription-only visits (MDD-001, roadmap); post-visit communication coaching (roadmap); a real human interpreter connection; accounts, persistence, and privacy work; the other eight roadmap languages.

## Impact

- `server/`: contracts, the turn graph (manner), the voice delivery tables, a trust advisor replacing the empathy advisor, the patient signal and closing check handlers, companion turns, a model timeout, interpreter lines in five languages, fixtures, and tests.
- `web/`: a design token layer and every stylesheet; the patient device; the controller's trust view, companion control, and closing check; manner labels and signal notices on the shared screen; end-to-end scripts.
- Native speaker review needed for the new labels and lines (all `_reviewer: pending`).
