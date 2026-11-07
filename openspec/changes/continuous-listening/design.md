# Design

## Context

Push-to-talk (IDR-001) gives each turn its speaker and language from the control pressed.
`turn.submit` (CDR-001) already carries both, so a new capture mode only has to supply them another way.
The physician speaks English and the patient speaks the visit's patient language, so the language of an utterance identifies its speaker.

## Goals and Non-Goals

- Goal: a visit can run without pressing a control per turn, with correct speaker labels in normal conversation.
- Goal: no server or contract change.
- Non-goal: telling apart two speakers of the same language.
- Non-goal, planned as a follow-up change: voice recognition, which learns each person's voice from the name introduction and breaks ties on short replies and tells companions from the patient; it needs its own decision record (vendor, and voiceprints as biometric data).

## Decisions

- **Recognition**: one continuous recogniser with language identification over the visit's two languages, per IDR-004 on the speech provider chosen in ADR-005.
- **Turn boundary**: the recogniser's end-of-utterance silence detection, with a configurable silence timeout (starting at about 800 ms) so a mid-sentence pause does not split a turn, per IDR-004.
- **Speaker**: physician language means physician, patient language means patient, per IDR-004; the turn is then submitted through the existing controller path, so name replies, read-back, and latency rows behave as for push-to-talk (CDR-001 unchanged).
- **Echo**: listening pauses while the shared speaking signal (below) says the voice is playing, and resumes after a short tail (about 300 ms, owned by the listener) once it stops, per IDR-004.
- **Other pauses**: while a dose read-back is pending, and while a push-to-talk control is held (the override), per IDR-004.
- **No correction**: the interpreter routes each utterance by its detected language into the other party's language, so a misdetection gives a redundant translation, not a lost one; push-to-talk covers anything said again, per IDR-004 (amended 2026-11-07).
  No visit channel change is needed (CDR-001 unchanged).
- **Latency**: end of speech becomes the recognised time minus the silence timeout, so the recognition figure stays comparable with push-to-talk.

### Shared speaking signal

One signal in `web/lib/speech.ts` says which item the interpreter's voice is saying right now, on `/control`, where `speak()` runs.
Hands-free listening pauses on it, and the controller reports it to the visit so other screens can follow; no other module adds a second one.
The shared screen on the TV never reads it directly: it learns of the voice only through those visit channel events, which belong to another change.

```ts
/** A turn or interpreter line, by the id its audio is asked for by, in one language. */
export interface Speaking { speechId: string; language: Language }
/** The item whose audio is audible now, whichever voice says it, or null. */
export function current(): Speaking | null;
export function isSpeaking(): boolean; // current() !== null
/** Calls the listener with the current item now, then on every change; returns an unsubscribe. */
export function onSpeaking(listener: (speaking: Speaking | null) => void): () => void;
```

- **Set** to an item when its audio element fires `playing`.
- **Cleared** to null when that item's audio ends, errors, or is refused, so the signal never sticks.
- **Back-to-back items** read item 1, then null, then item 2, since the queue starts an item only after the one before it has ended; listeners smooth that gap with their own tails.
  A start that arrives while another item is current hands over directly, and the earlier item's late end is ignored.
- **Fetching is not speaking**: waiting for audio to arrive is null, since nothing is audible.
- **No timing policy inside**: tails, debouncing, and easing belong to each listener.
- **Testable**: the state lives in `web/lib/speaking.ts`, which has no imports and is unit-tested without the speech SDK.

**Both voices play through one path.**
The server voice was already played by an audio element in `playStream`.
The Azure fallback used the SDK's own speaker output, and because `speech.ts` reuses one warmed synthesizer per language, that player receives every utterance as one endless stream: its `onAudioStart` fires once, and its end never fires.
Measured on a Sinhala turn (no server voice, so Azure speaks), the audio element's `ended` event never fired within 30 seconds.
So the Azure synthesizer now produces MP3 with no speaker output, and its chunks are streamed into `playStream` as Azure makes them, keeping the warm connection and the early start.
This also makes an Azure queue item last until its audio ends, as a server voice item already did, instead of finishing when synthesis completes.

The signal is independent of IDR-004 and changes no behaviour by itself, so it lands first.
It sits under ADR-005, as part of the speech module.

**Unit tests**: `npm test` runs `node --test` over `web/lib/**/*.test.mjs`, using Node's built-in runner with no new dependency.
EDR-002 records this runner for web unit tests (amended 2026-11-07).

## Risks and Trade-offs

- Short replies may be misdetected; the indicator shows it and push-to-talk remains.
  Voice recognition, enrolled during the name introduction, is the planned follow-up for short replies and companions.
- A patient answering in English is labelled physician; the physician corrects it or uses push-to-talk.
- Each language must be supported by the provider's language identification; unsupported languages keep hands-free disabled.

## Open Questions

None.
