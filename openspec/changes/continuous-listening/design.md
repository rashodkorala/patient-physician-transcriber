# Design

## Context

Push-to-talk (IDR-001) gives each turn its speaker and language from the control pressed.
`turn.submit` (CDR-001) already carries both, so a new capture mode only has to supply them another way.
The physician speaks English and the patient speaks the visit's patient language, so the language of an utterance identifies its speaker.

## Goals and Non-Goals

- Goal: a visit can run without pressing a control per turn, with correct speaker labels in normal conversation.
- Goal: no server or contract change.
- Non-goal: telling apart two speakers of the same language.

## Decisions

- **Recognition**: one continuous recogniser with language identification over the visit's two languages, per IDR-004 on the speech provider chosen in ADR-005.
- **Turn boundary**: the recogniser's end-of-utterance silence detection, with a configurable silence timeout (starting at about 800 ms) so a mid-sentence pause does not split a turn, per IDR-004.
- **Speaker**: physician language means physician, patient language means patient, per IDR-004; the turn is then submitted through the existing controller path, so name replies, read-back, and latency rows behave as for push-to-talk (CDR-001 unchanged).
- **Echo**: listening pauses while the shared speaking signal (below) says the voice is playing, and resumes after a short tail (about 300 ms, owned by the listener) once it stops, per IDR-004.
- **Other pauses**: while a dose read-back is pending, and while a push-to-talk control is held (the override), per IDR-004.
- **Correction**: a "wrong speaker" action on a turn discards it through the existing discard path and resubmits the same text with the other speaker and language, per IDR-004.
- **Latency**: end of speech becomes the recognised time minus the silence timeout, so the recognition figure stays comparable with push-to-talk.

### Shared speaking signal

One signal in `web/lib/speech.ts` says whether the interpreter's voice is audible.
Hands-free listening uses it to pause, and the controller's animated orb uses it to animate; no other module adds a second one.

```ts
/** True while the interpreter's voice is audible, whichever voice says it. */
export function isSpeaking(): boolean;
/** Calls the listener with the current state now, then on every change; returns an unsubscribe. */
export function onSpeaking(listener: (speaking: boolean) => void): () => void;
```

- **True** from the moment audio actually starts for an item in the `speak()` queue: `onplaying` on the server voice's audio element, or the Azure player's start.
- **False** when that item's audio has really ended and the next item's audio has not started; if the next item is already loaded, the state stays `true` across the boundary, and any short gap while it loads is smoothed by each listener's own tail.
- **Covers both voices**: the server voice (`playStream`) and the Azure fallback (`speakWithAzure`).
  For Azure, the end is the `SpeakerAudioDestination` `onAudioEnd` event, not `speakTextAsync` completing, which fires when synthesis finishes and can be before playback ends.
- **Errors**: a failed or refused item ends its `true` state like a finished one, so the signal never sticks on.
- **Fetching is not speaking**: waiting for audio to arrive is `false`, since nothing is audible.
- **No timing policy inside**: tails, debouncing, and animation easing belong to each listener, so the two features can tune them separately.
- **Testable**: the state change is a small pure counter around the queue, unit-tested without the speech SDK.

The signal is independent of IDR-004 and changes no behaviour by itself, so it can land first for the orb.
It still sits under ADR-005, as part of the speech module.

## Risks and Trade-offs

- Short replies may be misdetected; the indicator and correction cover this, and push-to-talk remains.
- A patient answering in English is labelled physician; the physician corrects it or uses push-to-talk.
- Each language must be supported by the provider's language identification; unsupported languages keep hands-free disabled.

## Open Questions

- IDR-004 is proposed and needs a human verdict before implementation.
- Whether the "wrong speaker" correction can reuse an existing discard path for a settled turn, or needs a small visit channel addition; if the latter, it needs a CDR-001 amendment first.
