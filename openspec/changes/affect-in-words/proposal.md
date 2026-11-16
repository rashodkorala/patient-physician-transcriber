# Proposal

## Why

After testing, tone variation in the ElevenLabs voice does not work: a worried patient is relayed in a voice that does not carry it.
The trust-across-the-barrier change gave the voice a delivery per manner and per emotion, and that is the part that failed.
Rashod's direction on 2026-11-16: keep the voice constant and express affect in words, as a human interpreter would say "the patient sounds worried".

## What Changes

- The interpreter's voice is constant for every turn, in both directions.
  No delivery varies by manner, emotion, or certainty, and interpreter lines (introductions, name questions, signal lines) use the same single delivery, so there is one delivery everywhere.
- For a patient or companion turn whose affect is clearly not plain, the spoken relay to the physician carries one hedged affect phrase inside the reporting frame only, for example "The patient says, sounding worried, ...".
  Plain turns get no phrase.
- Physician turns keep the existing frame adverb and, for the patient, the existing manner label.
- The patient's manner and emotion still go to the physician's controller as a label and never appear as a label on the shared screen or the patient's device.
  The one change to privacy: the frame phrase is spoken aloud in the room in the physician's language, and it sits inside the translation text, so it appears wherever that text is shown (see design, "Privacy").
- Meaning never changes: one phrase, frame only; instructions, certainty, and critical values unchanged; the critical value check and the tone check behave as before and accept the phrase.
- Known gaps are recorded plainly in `docs/known-gaps.md` and not fixed: affect is inferred from the words only and not from the audio, the product uses hosted APIs rather than its own models hosted on AWS and trained on real consultation data, and the voice is not expressive.

## Out of scope

- Reading affect from the audio, prosody, or any new model.
- Fixing the known gaps, including owned models, hosting, or training data.
- Any change to the wire contract (no new field on `TurnResult`, `TurnCaption`, or a trust update).
- The physician's frame adverb rule and the caption manner label for physician turns (IDR-005), apart from removing their voice delivery.
- Compliance, data residency, and vendor terms, which are explicitly not weighed at this stage.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `manner-in-relay`: "Manner in the interpreter's voice" becomes a constant voice plus affect in the frame; "Manner is private for the patient" is amended for the spoken frame phrase; "Manner never changes meaning" is extended to cover the patient-turn frame phrase.
  The capability's Purpose text, which the delta format cannot carry, is updated when the change is synced or archived.

## Decisions relied on

- Accepted by rashodkorala on 2026-11-16 (task group 0): MDD-006 (affect in words), IDR-006 (affect phrase in the frame and one constant voice delivery).
- Existing records this change amends in behaviour, by reference and not superseded, so their status stays accepted: IDR-005 (voice delivery per manner and emotion), ADR-010 (tone by emotion and certainty), MDD-005 (decisions 2 and 3).
- Accepted, relied on as they stand: MDD-004, ADR-004 (turn graph), ADR-006 (models), CDR-002 (turn result), CDR-008 (captions carry no patient manner), EDR-002 (testing).
  Each lists `affect-in-words` in its `related_changes` as of 2026-11-16.
- Accepted and already binding: MDD-001, MDD-002, EDR-001.

## Impact

- `server/voice.py`: one fixed delivery; the per-manner, per-emotion, and certainty tables are removed.
- `server/graph/turn_graph.py`, `server/fake_model.py`: the translate prompt, the tone-check wording, and the fake model's phrase.
- `server/main.py`: the speak gate uses the constant delivery.
- Tests: `server/tests/test_voice.py`, `server/tests/test_turn_graph.py`, `server/tests/test_trust_channel.py`, and `web/e2e/screen-manner.mjs`.
- `docs/known-gaps.md` (new), and the `manner-in-relay` main spec.
