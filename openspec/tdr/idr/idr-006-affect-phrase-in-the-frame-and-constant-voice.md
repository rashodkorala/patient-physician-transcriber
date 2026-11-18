---
id: idr-006
title: "Affect phrase in the reporting frame, and one constant voice delivery"
status: accepted
date: 2026-11-16
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: implementation
related_decisions: [mdd-006, mdd-005, idr-005, adr-004, adr-010, cdr-002, cdr-008]
related_specs: [manner-in-relay]
related_changes: [affect-in-words]
ai_context:
  implementation_priorities:
    - "The translate call already reads emotion; it now also writes one hedged affect phrase in the frame for a patient or companion turn whose emotion is not calm; no extra model call"
    - "The voice has one fixed Delivery used for every turn; the per-manner, per-emotion, and certainty tables are removed"
    - "Interpreter lines (introduction, name questions, signal lines) use the same single constant delivery as turn relays; there is no separate line delivery"
  framework_hints:
    - "Prompt and tone check: server/graph/turn_graph.py; delivery: server/voice.py; the fake model in server/fake_model.py must write the phrase for tests"
    - "Phrase by emotion, in the target language's natural hedged form: worried - sounding worried; frightened - sounding frightened; embarrassed - sounding embarrassed; in_pain - sounding as if in pain; relieved - sounding relieved; confused - sounding confused; calm - none. No phrase when the speaker's own words already state the feeling (MDD-006 decision 8): the words carry it, and the emotion read and the controller label stay the same"
  validation_rules:
    - "At most one affect phrase per relay, inside the opening frame, never in a later sentence"
    - "A calm turn has no phrase"
    - "A physician turn never gets an affect phrase; it keeps the IDR-005 frame adverb rule"
    - "The phrase never changes an instruction, a certainty word, a number, or a critical value"
    - "TurnResult, TurnCaption, and every public projection gain no new field"
affects: [server/graph/turn_graph.py, server/voice.py, server/fake_model.py, server/main.py]
implementation_refs:
  - server/voice.py
  - server/main.py
  - server/graph/turn_graph.py
  - server/fake_model.py
  - server/contracts.py
  - server/visit_store.py
  - server/chains/snapshot.py
  - server/chains/note.py
  - server/chains/summary.py
test_refs:
  - server/tests/test_voice.py::test_every_turn_and_interpreter_line_gets_the_one_constant_delivery_idr_006
  - server/tests/test_voice.py::test_text_brackets_cannot_act_as_performance_tags_idr_006
  - server/tests/test_turn_graph.py::test_prompts_define_the_affect_phrase_rule_idr_006
  - server/tests/test_turn_graph.py::test_worried_patient_turn_has_exactly_one_phrase_in_the_frame_idr_006
  - server/tests/test_turn_graph.py::test_calm_patient_turn_has_no_phrase_idr_006
  - server/tests/test_turn_graph.py::test_companion_turn_names_the_companion_and_carries_one_phrase_idr_006
  - server/tests/test_turn_graph.py::test_physician_turn_never_gets_an_affect_phrase_idr_006
  - server/tests/test_turn_graph.py::test_frame_phrase_passes_the_tone_check_idr_006
  - server/tests/test_turn_graph.py::test_phrase_that_makes_the_statement_more_certain_fails_the_tone_check_idr_006
  - server/tests/test_turn_graph.py::test_worried_patient_dose_keeps_its_value_and_the_check_still_blocks_a_change_idr_006
  - server/tests/test_contracts.py::test_affect_in_words_adds_no_wire_field_idr_006
  - server/tests/test_trust_channel.py::test_worried_patient_label_reaches_the_controller_only_and_the_phrase_only_the_translation_idr_006
  - server/tests/test_trust_channel.py::test_speak_gate_speaks_the_worried_patient_relay_with_its_phrase_and_refuses_non_final_turns_idr_006
  - server/tests/test_turn_graph.py::test_listed_phrase_that_undermines_a_stated_dose_fails_the_tone_check_idr_006
  - server/tests/test_turn_graph.py::test_close_paraphrase_counts_as_the_frame_phrase_idr_006
  - server/tests/test_turn_graph.py::test_affect_phrase_on_a_physician_relay_is_never_final_idr_006
  - server/tests/test_turn_graph.py::test_physician_who_says_sounding_is_not_mistaken_for_an_affect_phrase_idr_006
  - server/tests/test_turn_graph.py::test_reported_phrase_must_appear_once_and_not_on_a_calm_turn_idr_006
  - server/tests/test_turn_graph.py::test_patient_turn_relayed_to_the_patient_carries_no_phrase_idr_006
  - server/tests/test_turn_graph.py::test_turn_result_keeps_the_phrase_off_the_wire_idr_006
  - server/tests/test_grounded_checks.py::test_the_affect_phrase_is_left_out_of_every_source_idr_006
  - server/tests/test_grounded_checks.py::test_without_affect_phrase_idr_006
  - server/tests/test_note_summary_channel.py::test_the_affect_phrase_never_reaches_the_note_or_the_summary_idr_006
  - server/tests/test_trust_channel.py::test_patient_turn_in_the_physicians_language_is_relayed_to_the_patient_without_a_phrase_idr_006
  - web/e2e/screen-manner.mjs
  - web/e2e/trust-view.mjs
---

# IDR-006: Affect phrase in the reporting frame, and one constant voice delivery

> Implementation Decision Record. Only a human may set `status: accepted`.

## Summary

The translate call writes one hedged affect phrase into the opening frame of a patient or companion relay whose emotion is not calm, and the voice speaks every turn with one fixed delivery.
This implements MDD-006 and amends the voice-delivery parts of IDR-005 and ADR-010.

## Context

- **Feature or component**: the translate prompt and tone check, and the voice delivery table.
- **Technical requirements**: no added latency, no new model call, critical value and tone checks unchanged in force, and no change to the wire contract.
- **Constraints**: affect is read from the words only; the physician's frame adverb and caption label stay as IDR-005 decided.

## Decision

- **Constant delivery.** `server/voice.py` keeps one `Delivery` for turn relays.
  `MANNER_DELIVERY`, `EMOTION_DELIVERY`, `delivery_for`, `delivery_for_turn`, and the certainty steadiness are removed, with their completeness assertions.
  `LINE_DELIVERY` and its warm "[warmly]" tag are removed too: interpreter lines (introduction, name questions, signal lines) use the same single constant delivery as turn relays, so there is one delivery everywhere (project lead, 2026-11-16).
  The project lead approved removing the `[calm]` performance tag after hearing breathy playback during the demo rehearsal.
  All lines use stability 0.55 and the same configured voice without performance tags.
- **Frame phrase.** For a patient or companion turn the translate prompt tells the model: when the speaker's emotion is clearly not calm, add one hedged phrase naming it inside the opening frame, in the target language's natural form ("The patient says, sounding worried, that ..."), once, never anywhere else, and never in a way that changes an instruction, a certainty word, a number, or a medication.
  A calm turn gets no phrase.
  The model's `emotion` read decides, so the phrase and the controller label agree.
  When the speaker's own words already state the feeling ("I am very worried"), the relay keeps those words and carries no phrase; a phrase beside them doubles the feeling.
  The tone check fails a doubled relay and passes the same relay without the phrase; a feeling stated in the speaker's own words is content, never an added phrase.
- **Tone check.** The tone check is told the frame may carry one such hedged phrase for a patient turn, as it already accepts one manner adverb for a physician turn.
  It still fails a relay whose seriousness or certainty changed, or that adds advice or an answer.
- **Critical values.** The critical value check is untouched; the frame adds no number.
- **Visibility.** The phrase is part of `translation`, so it is spoken and appears in the caption's translation text and the record; no manner or emotion field or label is added to any public projection.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| A fixed English phrase table added by code | Reviewable, no model wording | Wrong in other target languages and breaks natural reported speech | The target is the physician's language, which can change |
| A second model call to add the phrase | Cleaner prompt | Adds latency and a second place for meaning to drift | Same call as emotion |
| A separate spoken sentence after the relay | Simple to place | Not inside the frame; more words in the room; harder for the tone check | Frame only |
| Keep a small voice variation as well | Some audible cue | Tested and did not work; keeps tables to maintain | The project lead's test result |

## Consequences

- **Positive**: less code, one voice, offline-testable behaviour.
- **Negative**: the phrase wording in other physician languages is unreviewed; certainty is no longer audible in the voice and is carried only by the words.
- **Risks and mitigations**: an over-read emotion, mitigated by the calm default and hedging; a phrase added to a physician turn, mitigated by a test.

## Implementation

`server/voice.py`, `server/graph/turn_graph.py` (prompt, tone-check wording), `server/fake_model.py`, `server/main.py` (the speak gate), and tests named for this record.
Code carries `@implements IDR-006: Affect phrase in the reporting frame, and one constant voice delivery`.

## Review Notes

- 2026-11-16, Claude (agent): Drafted alongside MDD-006.
  Awaiting human review; do not implement until accepted.
- 2026-11-16, rashodkorala: Accepted in session ("Accept both"), together with MDD-006.
  Recorded by Claude (agent) at rashodkorala's explicit request.
  His answers to the design's Open Questions: (1) the affect phrase stays visible in the caption translation text, with no public and private text split; (2) for patient and companion turns the phrase is driven by `emotion`, not `manner`; (3) certainty steadiness in the voice is removed too, so certainty is carried by the words only; (4) interpreter lines do not keep a separate warm delivery and use the same single constant delivery as turn relays, which corrects the draft's default.
  He also decided that IDR-005, MDD-005, and ADR-010 are amended by reference and not superseded; their status stays accepted.
- 2026-11-16, rashodkorala: amended ("yes to time of day and IDR-006"), to follow MDD-006 decision 8: "sounding frightened" joins the phrases, and a relay carries no phrase when the speaker's own words already state the feeling (framework hints and the Frame phrase decision).
  Recorded by Claude (agent) at rashodkorala's explicit request. The status stays accepted.
