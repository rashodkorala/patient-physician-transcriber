---
id: idr-004
title: "Hands-free continuous listening, with the speaker found by spoken language"
status: proposed
date: 2026-11-06
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: implementation
related_decisions: [idr-001, adr-005, cdr-001, mdd-003, edr-002]
related_specs: []
related_changes: [continuous-listening]
ai_context:
  implementation_priorities:
    - "Push-to-talk (IDR-001) stays the default and the fallback; hands-free is an opt-in mode on the controller"
    - "The speaker is derived from the detected language: the physician language means physician, the patient language means patient"
    - "The microphone is never transcribed while the interpreter's own voice is playing"
  framework_hints:
    - "Azure Speech continuous language identification (LanguageIdMode Continuous) with the visit's two languages as candidates"
    - "Azure end-of-utterance silence segmentation is the turn boundary; the silence timeout is configurable"
    - "Refresh the authorisation token on the live recogniser before it expires"
  validation_rules:
    - "Every turn still records speaker and language explicitly, through the unchanged turn.submit event (CDR-001)"
    - "No turn is submitted from audio captured while translated speech plays"
    - "The physician can correct a wrong speaker label in one action"
affects: [web/lib/speech.ts, web/components/Controller.tsx]
implementation_refs: []
test_refs: []
---

# IDR-004: Hands-free continuous listening, with the speaker found by spoken language

> Implementation Decision Record. Only a human may set `status: accepted`.

## Summary

Add an opt-in hands-free mode to the physician controller: the microphone stays open, each utterance is segmented by silence, and its speaker is taken from the language it was spoken in.
Push-to-talk per speaker (IDR-001) remains the default, the fallback, and a manual override.

## Context

- **Feature or component**: turn capture on `/control`.
- **Technical requirements**: correct speaker and language on every turn; no change to the visit channel contract (CDR-001); latency comparable with push-to-talk.
- **Constraints**: IDR-001 ruled out voice diarisation because mislabels break provenance.
  The two parties in a visit never share a language: the physician speaks English (`en-CA`) and the patient speaks the visit's patient language.
  The interpreter speaks every translation aloud in the room, so an open microphone hears it.

## Decision

1. `web/lib/speech.ts` gains a continuous capture mode beside the push-to-talk capture.
   It runs one Azure recogniser (ADR-005) with continuous language identification over exactly two candidates, the physician language and the patient language.
   Each recognised utterance reports its text, detected language, confidence, and end-of-speech time.
2. The controller maps the detected language to the speaker and submits through the existing path, so name replies, read-back, latency, and `turn.submit` are unchanged.
3. Listening pauses while the interpreter's voice is audible, read from the one shared speaking signal in `web/lib/speech.ts` (also used by the controller's orb; see the change's design.md), and resumes a short moment after it stops.
   It also pauses while a dose read-back is pending, and while the physician holds a push-to-talk control.
4. The controller shows which speaker was last heard, and each turn offers a one-action "wrong speaker" correction that discards the turn and resubmits it with the other speaker.
5. The mode is chosen per visit on the controller; it is off by default.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Voice diarisation (Azure conversation transcription or similar) | Works for same-language speakers | Error-prone live, needs enrolment or warm-up, mislabels break provenance (the IDR-001 reason) | The language difference already separates the two parties, more reliably |
| Keep push-to-talk only | Most reliable labels | Physician presses for both speakers all visit | Hands-free is the requested experience; push-to-talk stays available |
| Two microphones, one per party | Speaker known from the device | Extra hardware, cross-talk between nearby microphones | More setup for a demo laptop than language identification |

## Consequences

- **Positive**: hands-free visits with no server or contract change; push-to-talk remains for anything the detection gets wrong.
- **Negative**: short replies ("yes", "ok") may be misdetected because language identification needs some speech; a patient answering in English, or code-switching heavily, is labelled physician; overlapping speech is not handled.
- **Risks and mitigations**:
  - Echo of the translated voice: listening pauses while it plays (decision point 3).
  - Mislabels: a visible last-speaker indicator and one-action correction; push-to-talk override.
  - Language support: each candidate language must be supported by Azure language identification; confirm `pa-IN`, `fr-CA`, `ta-LK`, and `si-LK` before building, and keep hands-free disabled for any language that is not.

## Implementation

`web/lib/speech.ts` adds the continuous capture and a pause hook on the voice queue.
`web/components/Controller.tsx` adds the mode toggle, the language-to-speaker mapping, the indicator, and the correction.
Code governed by this record carries `@implements IDR-004: Hands-free continuous listening, with the speaker found by spoken language`.
Tests: a unit test for the mapping and the pause rule, and an end-to-end hands-free run in `web/e2e/` with a fake recogniser (EDR-002).

## Review Notes

- 2026-11-06, Claude (agent): Drafted as a proposal at rashodkorala's request for continuous listening with speaker detection. Awaiting human review; do not implement until accepted.
