# Proposal

## Why

Today the physician holds a speaker control for every turn, for both people (IDR-001).
That keeps labels reliable but keeps the physician's hands and attention on the controller for the whole visit.
A hands-free mode lets the conversation flow while still recording who said what, in which language.

## What Changes

- An opt-in hands-free mode on the physician controller: the microphone stays open and each utterance becomes a turn when the speaker pauses.
- The speaker of each turn is decided by the language spoken, since the physician and the patient always speak different languages in a visit.
- The interpreter never transcribes its own spoken translations.
- The controller shows who was last heard, and the physician can correct a wrong speaker in one action.
- Push-to-talk stays the default, the fallback, and a manual override while hands-free is on.

## Capabilities

### New Capabilities

- `hands-free-turns`: continuous listening with the speaker found by spoken language.

### Modified Capabilities

None; push-to-talk turns keep their current behaviour.

## Decisions

- Relies on IDR-001 (push-to-talk, kept as the fallback), ADR-005 (speech provider), CDR-001 (visit channel, unchanged), and EDR-002 (testing).
- Needs IDR-004 (proposed): hands-free continuous listening, with the speaker found by spoken language.

## Out of Scope

- Voice diarisation, and visits where both parties speak the same language.
- Companions or third speakers.
- Overlapping speech.
- Any server or visit channel contract change.

## Impact

- `web/lib/speech.ts`, `web/components/Controller.tsx`, and its stylesheet.
- New end-to-end test in `web/e2e/`.
