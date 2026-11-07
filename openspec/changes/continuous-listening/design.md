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
- **Echo**: the voice queue in `web/lib/speech.ts` already plays one item at a time; listening pauses while it has anything queued or playing and resumes shortly after it drains, per IDR-004.
- **Other pauses**: while a dose read-back is pending, and while a push-to-talk control is held (the override), per IDR-004.
- **Correction**: a "wrong speaker" action on a turn discards it through the existing discard path and resubmits the same text with the other speaker and language, per IDR-004.
- **Latency**: end of speech becomes the recognised time minus the silence timeout, so the recognition figure stays comparable with push-to-talk.

## Risks and Trade-offs

- Short replies may be misdetected; the indicator and correction cover this, and push-to-talk remains.
- A patient answering in English is labelled physician; the physician corrects it or uses push-to-talk.
- Each language must be supported by the provider's language identification; unsupported languages keep hands-free disabled.

## Open Questions

- IDR-004 is proposed and needs a human verdict before implementation.
- Whether the "wrong speaker" correction can reuse an existing discard path for a settled turn, or needs a small visit channel addition; if the latter, it needs a CDR-001 amendment first.
