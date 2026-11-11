---
id: mdd-005
title: "Trust across the barrier: the patient has a voice, the physician's manner is carried, and the physician sees how it is landing"
status: accepted
date: 2026-11-10
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: strategy
related_decisions: [mdd-001, mdd-004, adr-002, adr-003, adr-010, cdr-002, cdr-003]
related_specs: [patient-voice, manner-in-relay, trust-signals-for-the-physician, companion-turns]
related_changes: [trust-across-the-barrier]
ai_context:
  implementation_priorities:
    - "Give the patient their own controls during the visit, in their own language, on their own device: I did not understand, please slow down, say that again, pause, and a human interpreter"
    - "Carry how the physician said something, not only what: in the interpreter's voice, in the reporting frame when words alone would lose it, and as a short label the patient can read"
    - "Show the physician, privately, how the visit is landing: the patient's emotion over time, whether reassurance landed, every patient signal, and a culture cue when a topic is sensitive in the patient's culture"
    - "Let a companion speak as a labelled third speaker in the patient's language"
    - "Let the interpreter close the loop by asking the patient, in their language, whether anything should be explained again"
  framework_hints:
    - "Contract: CDR-008; manner vocabulary and voice delivery: IDR-005; interface: ADR-012"
    - "The patient's device is the existing review role, now a screen the patient holds throughout the visit"
  validation_rules:
    - "The patient's emotion is never shown on a shared or patient screen; it stays with the physician, as today"
    - "The physician's manner is read from the words that were said and is labelled as such; it never changes certainty, seriousness, or any critical value"
    - "A patient signal is never silently dropped: it reaches the physician's controller, the shared screen in both languages, and the record"
    - "Nothing in this layer is spoken aloud unless it passed the speak gate like every other line"
affects: [server/, web/]
implementation_refs:
  - server/trust.py
  - server/main.py
  - server/visit_store.py
  - server/graph/turn_graph.py
  - server/voice.py
  - server/introduction.py
  - web/components/PatientScreen.tsx
  - web/components/Controller.tsx
  - web/app/patient/page.tsx
test_refs:
  - server/tests/test_trust.py
  - server/tests/test_trust_channel.py
  - server/tests/test_turn_graph.py::test_manner_is_read_in_the_translate_call_and_labels_a_physician_turn_idr_005
  - server/tests/test_voice.py::test_every_manner_has_a_delivery_and_physician_turns_follow_it_idr_005
  - web/e2e/patient-voice.mjs
  - web/e2e/trust-view.mjs
  - web/e2e/screen-manner.mjs
---

# MDD-005: Trust across the barrier: the patient has a voice, the physician's manner is carried, and the physician sees how it is landing

> Major Design Decision. Only a human may set `status: accepted`.

## Summary

Interpretation that is accurate but flat does not build trust.
This decision adds a trust layer on top of the live interpreter: the patient gets a voice of their own during the visit, the physician's manner travels with their words, the physician privately sees how the conversation is landing, a companion can speak as a labelled third speaker, and the interpreter can close the loop by asking the patient whether anything should be explained again.

## Context

- **Business Context**: Rashod's direction on 2026-11-10: the interpreter must help both parties build trust with each other, because tone and emotion are what translation loses first.
  Today the patient has no control during the visit (pause and the interpreter button sit on the physician's controller), the physician's manner is not carried (captions label the translation's register, and the voice follows the speaker's emotion rather than how they meant it), and nothing tells the physician whether their reassurance reached the patient.
- **Strategic Drivers**: professional interpreters carry affect and register, broker culture when it matters, and ask for clarification; the product should do the same, visibly and checkably.
- **Constraints**: manner can only be read from the words said, since recognition gives no prosody; the patient's emotion stays private to the physician (demo spec: "Patient emotion stays with the physician"); every spoken line still passes the speak gate; model calls must not add latency to the turn.

## Decision

1. **The patient has a voice.** The patient's own device (the review role, route `/patient`) carries, during the visit and in the patient's language first: "I did not understand", "Please slow down", "Say that again", "Pause", and "I want a human interpreter".
   A signal is shown on the shared screen in both languages, is relayed to the physician by the interpreter in the physician's language, is recorded in the visit record, and is shown on the physician's controller.
   "Say that again" replays the last spoken translation in the patient's language without a new model call.
2. **The physician's manner is carried.** Every turn carries a `manner` read from the words said (IDR-005).
   For a physician turn it is carried three ways: the interpreter's voice delivers the relay in that manner; the reporting frame may name it when the words alone would lose it ("Dr Patel is saying, gently, that..."); and the caption shows a short label in the patient's language ("Said gently").
   Manner never changes how certain or serious the news is, and never touches a critical value.
3. **The patient's emotion stays private.** Patient and companion captions carry no manner or emotion label on any shared or patient screen.
   The interpreter's voice conveys the patient's affect to the physician as a human interpreter would, and the physician's controller shows the emotion, as today.
4. **The physician sees how it is landing.** The controller shows a private trust view: the patient's emotion turn by turn, whether a reassurance landed (a worried patient who sounds calm or relieved after a reassuring, warm, gentle, or encouraging physician turn), every patient signal, and a culture cue when the physician's turn touches a topic the patient language's tone guide marks as sensitive.
   Cues are suggestions in English for the physician only and are never shown to the patient or written into the note or the summary.
5. **A companion can speak.** The controller has a third speaker control for a companion speaking the patient's language; the turn is labelled companion everywhere, relayed as "the patient's companion is saying", and tagged `companion_stated` in the note.
6. **The interpreter closes the loop.** A controller control makes the interpreter ask the patient, in their language, whether anything the doctor said should be explained again, with the English shown to the physician.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Show both parties' emotions on the shared screen | Symmetric | Exposes a vulnerable patient's embarrassment or fear to the room | Asymmetry is deliberate: the physician speaks in a professional role; the patient does not |
| Read manner from audio prosody | Truer to delivery | No prosody from recognition; audio emotion models are unreliable across languages | Read from words, labelled honestly as such; revisit when prosody is available |
| Patient signals through the physician's controller only | No new device work | The patient must interrupt in a language they do not speak, which is the barrier itself | The patient needs their own control |
| Post-visit communication coaching only (roadmap) | Already specified | Too late to help this patient in this visit | Live, private, and small; the roadmap coaching stays for later |

## Consequences

- **Positive**: the patient can act without permission or English; the physician's care is audible and readable in the patient's language; the physician learns in the moment when something did not land.
- **Negative**: one more device in the room; one background model call per turn for cues; more content to review with native speakers (labels, lines).
- **Risks and mitigations**: a wrong manner label would mislead the patient, mitigated by reading manner conservatively (default `plain`), labelling it as read from the words, and reviewing the label set with the speakers; signal spam, mitigated by a two second hold per device.

## Implementation

The `trust-across-the-barrier` OpenSpec change: CDR-008 for the channel, IDR-005 for the manner vocabulary and voice delivery, and ADR-012 for the interface.
Code carries `@implements MDD-005: Trust across the barrier`.

## Review Notes

- 2026-11-10, Claude (agent): Drafted from rashodkorala's direction in session ("it needs to help both parties in building trust with each other since that's a bigger role when it comes to translation as tone and emotions conveyed can be lost. find a solution for this and build this platform").
- 2026-11-10, rashodkorala: Blanket authorisation given in session: "go through the spec update it by urself, i have given permission ... if any decisions i have made are not good enough you are good to change them. i will review once this is fully built and give you a proper answer." Recorded as accepted by Claude (agent) at rashodkorala's explicit request; rashodkorala reviews the built result and may reject or amend this record then.
