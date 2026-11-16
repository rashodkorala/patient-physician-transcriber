# Design

## Context

Motivation and scope: `proposal.md`, MDD-006, and IDR-006.
Behaviour: `specs/manner-in-relay/spec.md`.
Today one translate call (ADR-004, ADR-006) reads emotion, certainty, and manner, and writes a reported-speech relay; the server then speaks the settled text with a delivery chosen from fixed tables (IDR-005, ADR-010).
Testing showed the voice does not carry the tags, so the words must carry the affect.

Constraints: demo night prototype; every existing end-to-end script keeps passing; nothing is spoken without the speak gate; no model call is added; compliance and data concerns are explicitly not weighed.

## Goals / Non-Goals

**Goals:**
- A worried patient is heard as worried by the physician, through words.
- One constant voice, with less code and fewer tables.
- No change to meaning, to the critical value check, or to the wire contract.

**Non-Goals:**
- Prosody, owned models, hosting, or training data (recorded as known gaps).
- Any change to physician turns' words.

## Decisions

### 1. One constant delivery (per MDD-006, IDR-006, amends ADR-010 and IDR-005)

`server/voice.py` keeps one `Delivery` for every turn relay, both directions, and for every interpreter line (introduction, name questions, signal lines).
The `MANNER_DELIVERY` and `EMOTION_DELIVERY` tables, `delivery_for`, `delivery_for_turn`, the certainty steadiness, `LINE_DELIVERY` with its "[warmly]" tag, and their completeness assertions are removed.
Certainty is carried by the words only.
Alternative: keep a small variation.
Rejected: it was tested and did not work, and it keeps tables to maintain.
The `manner` and `emotion` read by the translate call are still produced and still reach the controller; they no longer drive the voice.

### 2. The affect phrase is written in the translate call (per IDR-006, ADR-004)

For a patient or companion turn, the translate prompt adds: when the speaker's emotion is clearly not calm, name it once with a hedged phrase inside the opening frame, in the target language's natural form; a calm turn gets no phrase.
The phrase follows the model's `emotion`, so it agrees with the controller label.
The model's wording in the physician's language is accepted for the prototype; the phrases per emotion are suggestions in the prompt, not a code table, because the target language can vary.
Alternative: a fixed English phrase table in code.
Rejected: wrong for other target languages and breaks natural reported speech.

The phrase is only ever for the physician (review fix, 2026-11-16).
The server tells the translate call who the listener is: a patient or companion turn spoken in the physician's language is relayed to the patient, so it carries no phrase.
The manner adverb is for physician turns only, and a patient or companion frame carries at most the one affect phrase.
The model also returns the phrase exactly as written (`affect_phrase` in the draft), so code can check it and keep it separable; it is never a wire field.

### 3. The tone check and the critical value check (per ADR-006, IDR-006)

The tone check is told who spoke and who the relay is for.
For a patient or companion turn relayed to the physician, one hedged affect phrase in the frame is acceptable in itself, as one manner adverb is for a physician turn; the same meaning in another language, or a close paraphrase such as "sounding anxious", counts as that phrase.
Affect wording anywhere else fails meaning_preserved: a phrase on a physician turn or on a turn relayed to the patient, a manner adverb on a patient turn, a second phrase, or one outside the frame.
An acceptable phrase still fails certainty_preserved when it makes the statement more or less certain or serious, for example "sounding confused" in front of a dose stated plainly.
It still fails a relay whose seriousness or certainty changed, or that adds advice or an answer.
Code adds a deterministic frame check (review fix, 2026-11-16): the reported phrase must appear exactly once, never on a calm turn, and only where it is allowed; and where no phrase is allowed, a back-translation that says "sounding" more often than the original fails.
A physician who says "sounding" keeps it in the original too, so counting avoids a false positive on legitimate words; the check reads English back-translations only, and elsewhere relies on the tone check.
The critical value check compares values and the frame adds none, so it needs no change.

### 4. Privacy (per CDR-008, MDD-006)

No new field is added to `TurnResult`, `TurnCaption`, or any public projection, so the existing guarantee holds: no manner or emotion label on the shared screen or the patient's device, and the controller still gets the label.
The spoken phrase is the change: it is spoken aloud in the room in the physician's language.
Because a caption's `translation` is the same text that is spoken, the phrase also sits inside that translation text wherever it is shown, including the shared screen's caption for the patient's turn and the record.
This is a consequence of "affect in words", not a separate label.
The project lead accepted it on 2026-11-16: the spoken text and the shown text are the same (see Resolved decisions).

The clinical note and the patient summary never restate the phrase (review fix, 2026-11-16).
The phrase is the interpreter's reading of how the patient sounded, not something the patient said, so it must not be recorded as patient-stated or read back to the patient.
The turn graph keeps the phrase on the turn result as a private, server-only attribute, and the frozen sources (ADR-011) take it out of each turn's and correction's translation before any generation sees them.
The note and summary prompts also say to leave how a speaker sounded out, for anything the deterministic step cannot see.
The chain keeps the translation as spoken, so the record still shows what was said in the room.

### 5. Known gaps are written down, not fixed (per MDD-006)

`docs/known-gaps.md` records: affect is inferred from the words only, so neutral words in a worried voice read as plain; the product uses hosted APIs (Claude, ElevenLabs, Azure) rather than its own models hosted on AWS and trained on real consultation data; and the voice is not expressive.
It also records that the note and summary leave the phrase out, and that the tone check's handling of phrases in other languages and paraphrases is unverified with a live model.

## Risks / Trade-offs

- An over-read emotion makes the physician hear a guess as fact; mitigated by the calm default, hedged wording, and the controller label showing the same read.
- Certainty is no longer audible in the voice, only in the words; the existing certainty rules in the prompt and tone check still hold.
- The phrase is unreviewed by speakers in the physician's language, and it is English-first in practice; native-speaker review of the patient-direction frames is an end-of-project item only.

## Migration Plan

Remove the delivery tables and update the prompt and tests in one pass, behind the existing fake-model stack.
Run `python3 scripts/check_tdr.py`, the server tests, and `node e2e/screen-manner.mjs`, `week2.mjs`, `patient-voice.mjs`, and `trust-view.mjs` on the fake-model stack.
No data migration and no contract change.

## Resolved decisions

The project lead (rashodkorala) answered the former Open Questions in session on 2026-11-16, and they are recorded in the Review Notes of MDD-006 and IDR-006.

- The affect phrase stays visible in the caption's `translation` text on the shared screen and the patient's device: the spoken text and the shown text are the same.
  There is no public and private text split and no CDR amendment.
- For a patient or companion turn the phrase is driven by `emotion`, not `manner`.
- Certainty steadiness in the voice is removed as well as per-emotion and per-manner delivery, so certainty is carried by the words only.
- Interpreter lines (introduction, name questions, signal lines) do not keep a separate warm delivery.
  They use the same single constant delivery as turn relays, so there is one delivery everywhere.
  This differs from the draft's default, which kept `LINE_DELIVERY`.
- MDD-005, IDR-005, and ADR-010 are amended by reference and not superseded; their status stays accepted.

## Open Questions

None.
