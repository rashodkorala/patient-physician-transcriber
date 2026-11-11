---
id: idr-005
title: "Manner: an eight-word vocabulary read from the words, carried into the voice, the frame, and the caption label"
status: accepted
date: 2026-11-10
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: implementation
related_decisions: [mdd-004, mdd-005, adr-002, adr-004, adr-010, cdr-002, cdr-008]
related_specs: [manner-in-relay]
related_changes: [trust-across-the-barrier]
ai_context:
  implementation_priorities:
    - "The translate call reads manner alongside emotion and certainty; no extra model call"
    - "Manner defaults to plain; the model is told to pick another value only when the words clearly carry it"
    - "Physician turns are voiced by manner; patient and companion turns by emotion, conveying the speaker's affect to the physician"
    - "The frame carries a manner adverb only for gentle, reassuring, serious, urgent, and apologetic, and only when the relayed words alone would lose it"
  framework_hints:
    - "Vocabulary and delivery tables live in server/voice.py; the Manner Literal in server/contracts.py"
    - "Caption labels are i18n keys mannerWarm, mannerReassuring, mannerGentle, mannerSerious, mannerUrgent, mannerApologetic, mannerEncouraging; plain has no label"
  validation_rules:
    - "A manner word never appears outside the reporting frame and never changes an instruction, a certainty word, or a critical value"
    - "The tone check treats a manner adverb in the frame as expected and still fails a relay whose seriousness or certainty changed"
    - "Every manner has a delivery; every emotion has a delivery; a unit test checks both tables are complete"
affects: [server/graph/turn_graph.py, server/voice.py, server/contracts.py, web/lib/i18n.ts]
implementation_refs:
  - server/graph/turn_graph.py
  - server/contracts.py
  - server/voice.py
  - server/fake_model.py
  - server/main.py
  - web/lib/contracts.ts
  - web/lib/i18n.ts
  - web/components/SharedScreen.tsx
  - web/components/PatientScreen.tsx
  - web/components/ReviewScreen.tsx
  - web/components/RecordView.tsx
  - web/components/Controller.tsx
test_refs:
  - server/tests/test_turn_graph.py::test_manner_is_read_in_the_translate_call_and_labels_a_physician_turn_idr_005
  - server/tests/test_turn_graph.py::test_patient_turn_has_a_private_manner_and_no_caption_label_idr_005
  - server/tests/test_turn_graph.py::test_prompts_define_manner_the_frame_rule_and_the_tone_check_allowance_idr_005
  - server/tests/test_voice.py::test_every_manner_has_a_delivery_and_physician_turns_follow_it_idr_005
  - server/tests/test_voice.py::test_patient_and_companion_turns_convey_the_speakers_emotion_idr_005
  - server/tests/test_trust_channel.py::test_physician_caption_carries_manner_and_patient_caption_never_does_cdr_008
  - web/lib/i18n.test.mjs
  - web/e2e/screen-manner.mjs
  - web/e2e/week2.mjs
  - web/e2e/patient-voice.mjs
---

# IDR-005: Manner: an eight-word vocabulary read from the words, carried into the voice, the frame, and the caption label

> Implementation Decision Record. Only a human may set `status: accepted`.

## Summary

Each turn gets one `manner` from a fixed set of eight, read by the translate call from the words said.
A physician turn's manner drives the interpreter's voice, may enter the reporting frame as one adverb, and is shown as a label in the patient's language.
A patient or companion turn's manner stays private; its emotion drives the voice that conveys it to the physician.

## Context

- **Technical drivers**: MDD-005 asks for the physician's manner to be carried; the turn graph already reads emotion and certainty in the translate call (ADR-004), so manner can be read in the same call at no latency cost.
  ElevenLabs Eleven v4 performs audio tags (ADR-010), today keyed on the speaker's emotion.
- **Quality attributes**: no added latency; honesty about what the label means; the critical value and tone checks unchanged in force.
- **Constraints**: manner is inferred from text alone.

## Decision

Vocabulary, what each means, and how it is delivered:

| Manner | Read when the words | Voice tag (physician turn) | Stability | Frame adverb | Label (English) |
|---|---|---|---|---|---|
| `plain` | inform or ask without marked feeling (the default) | `[calm]` | 0.55 | none | none |
| `warm` | are friendly and personal | `[warmly]` | 0.45 | none | Said warmly |
| `reassuring` | lower the listener's concern | `[reassuringly]` | 0.5 | "reassuringly" | Said with reassurance |
| `gentle` | handle difficult content with care | `[gently]` | 0.6 | "gently" | Said gently |
| `serious` | mark the content as grave | `[seriously]` | 0.65 | "seriously" | Said seriously |
| `urgent` | call for action now | `[urgently]` | 0.35 | "urgently" | Said urgently |
| `apologetic` | apologise or acknowledge a fault | `[apologetically]` | 0.5 | "apologetically" | Said with an apology |
| `encouraging` | praise or encourage | `[encouragingly]` | 0.45 | none | Said with encouragement |

Patient and companion turns are voiced to the physician by the speaker's emotion, conveying it rather than answering it: `calm` `[calm]`, `worried` `[concerned]`, `embarrassed` `[softly]`, `in_pain` `[gently]`, `relieved` `[warmly]`, `confused` `[hesitantly]`.
Certainty steadiness (ADR-010) still adds to stability.
Interpreter lines keep `[warmly]`.

Frame: the relay opens as today ("Dr Patel is saying ..."); when the manner is one of the five with a frame adverb and the model judges the relayed words alone would not carry it, the adverb goes inside the frame, once, in the target language's natural form.
The tone check is told the frame may carry such an adverb.

Label: the caption of a `final` physician turn carries `manner`; screens render the i18n label for the patient's language beneath the translation, and English beside it for the physician.
`plain` renders nothing.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Reuse `toneTags` as the label | Already exists | Describes the translation's register, not how the physician spoke; a physician can be warm without the relay being "empathetic" | Manner is about the speaker |
| A free-text manner | Expressive | Unreviewable, untranslatable, no fixed voice tag | A closed set the speakers can review |
| A separate model call for manner | Cleaner prompt | Adds latency to every turn | Same call as emotion |
| Voice patient turns by the listener's needs (today) | Soothing to the physician | Hides the patient's state from the one person who should feel it | Convey, do not answer |

## Consequences

- **Positive**: the physician's care is audible and readable in the patient's language; no latency change; everything stays checkable offline with the fake model.
- **Negative**: eight labels times five languages to review; the tags need the listening test to confirm they sound right.
- **Risks and mitigations**: a manner adverb in Punjabi or Tamil may read oddly, mitigated by the tone guides and by the speakers' review; over-labelling, mitigated by `plain` as the default.

## Implementation

`server/graph/turn_graph.py` (the `Draft.manner` field, prompt rules, tone-check wording), `server/voice.py` (`MANNER_DELIVERY`, `delivery_for_turn`), `server/contracts.py` (the `Manner` Literal, `TurnResult.manner`, `TurnCaption.manner`), `web/lib/i18n.ts` and `web/i18n/*.json` (labels).
Code carries `@implements IDR-005: Manner vocabulary and voice delivery`.

## Review Notes

- 2026-11-10, Claude (agent): Drafted alongside MDD-005.
- 2026-11-10, rashodkorala: Blanket authorisation given in session (see MDD-005). Recorded as accepted by Claude (agent) at rashodkorala's explicit request; rashodkorala reviews the built result.
