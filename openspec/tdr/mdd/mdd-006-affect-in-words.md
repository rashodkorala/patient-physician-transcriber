---
id: mdd-006
title: "Affect in words: a constant interpreter voice, with the patient's affect carried as one hedged phrase in the reporting frame"
status: accepted
date: 2026-11-16
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: strategy
related_decisions: [mdd-004, mdd-005, idr-005, idr-006, adr-010, cdr-008]
related_specs: [manner-in-relay]
related_changes: [affect-in-words]
ai_context:
  implementation_priorities:
    - "The interpreter's voice is the same for every turn in both directions; no delivery varies by manner, emotion, or certainty"
    - "For a patient or companion turn whose affect is clearly not plain, the relay to the physician carries exactly one hedged affect phrase, inside the reporting frame only"
    - "Physician turns keep the existing frame adverb and the existing caption manner label for the patient"
    - "The patient's manner and emotion still reach the physician's controller as a label, and never appear as a label on the shared screen or the patient's device"
    - "Record the known gaps plainly in docs/known-gaps.md; do not try to fix them here"
  framework_hints:
    - "Mechanics: IDR-006; the earlier voice-delivery decisions it amends are IDR-005 and ADR-010"
  validation_rules:
    - "The affect phrase appears once, inside the opening frame, and never changes an instruction, a certainty word, or a critical value"
    - "A plain or calm turn gets no phrase"
    - "The critical value check and the tone check behave as before; the tone check accepts the frame phrase"
    - "No wire field for manner or emotion is added to any public projection"
affects: [server/, web/e2e/, docs/]
implementation_refs: []
test_refs: []
---

# MDD-006: Affect in words: a constant interpreter voice, with the patient's affect carried as one hedged phrase in the reporting frame

> Major Design Decision. Only a human may set `status: accepted`.

## Summary

After testing, varying the ElevenLabs voice by tone does not work: a worried patient is relayed in a voice that does not carry it.
The interpreter's voice is now constant for every turn, and affect is expressed in words.
For a patient or companion turn whose affect is clearly not plain, the spoken relay to the physician carries one hedged affect phrase inside the reporting frame, for example "The patient says, sounding worried, ...".

## Context

- **Business Context**: Rashod's direction on 2026-11-16, after testing the live voice.
  MDD-005 decided that the patient's affect is conveyed to the physician through the voice (decision 3) and that the physician's manner is carried in the voice, the frame, and a label (decision 2).
  The voice half of that does not work with the chosen voice, so the words must do the job.
- **Strategic Drivers**: the physician should still hear that a patient is worried, and a human interpreter would say so.
  Words are checkable offline; voice tags are not.
- **Constraints**: demo night prototype.
  Affect is inferred from the words only (no prosody), the product uses hosted models and voices, and compliance and data concerns are explicitly not weighed yet (project lead).

## Decision

1. **The voice is constant.** The interpreter speaks every turn, physician, patient, and companion, and every interpreter line (introduction, name questions, signal lines), in one fixed delivery.
   No delivery varies by manner, emotion, certainty, or kind of line.
   Certainty is carried by the words only.
2. **Affect is expressed in words for patient and companion turns.**
   When the speaker's affect is clearly not plain, the relay to the physician carries one hedged affect phrase inside the reporting frame only, for example "The patient says, sounding worried, ...", "The patient's companion says, sounding embarrassed, ...".
   A plain turn gets no phrase.
   The phrase is hedged ("sounding", "seeming") because affect is inferred from the words alone.
3. **Physician turns are unchanged in words.** The frame adverb (gently, seriously, urgently, apologetically) and the caption manner label for the patient stay as IDR-005 decided.
   Only the voice delivery for physician turns is removed.
4. **Privacy.** The patient's manner and emotion still go to the physician's controller as a label, and no manner or emotion label appears on the shared screen or the patient's device.
   The one change: the frame phrase is part of the spoken relay, so it is now spoken aloud in the room in the physician's language, and, because a caption shows the same translation text that is spoken, it also appears inside that translation text wherever the translation is shown.
5. **Meaning never changes.** One affect phrase, frame only.
   Instructions, certainty, and critical values are unchanged, and the critical value check and the tone check behave as before and accept the frame phrase.
6. **Known gaps, recorded and not fixed here**, in `docs/known-gaps.md`:
   (a) affect is inferred from the words only, not from the audio, so neutral words said in a worried voice read as plain, which is why the wording is hedged;
   (b) the product uses hosted APIs (Claude, ElevenLabs, Azure) rather than its own models hosted on AWS and trained on real consultation data;
   (c) the voice is not expressive.
7. **Phrase source and visibility (project lead's answers, 2026-11-16).**
   For patient and companion turns the phrase is driven by `emotion`, not `manner`.
   The phrase stays visible in the caption translation text: spoken text and shown text are the same, with no public and private text split.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Keep tone variation in the voice (MDD-005, IDR-005) | Already built | Tested with the chosen voice and it does not carry affect | The project lead's test result |
| Tune the tags and stability further | No wording change | Tag-following is unreliable and cannot be checked offline | Words are reviewable and testable |
| Affect from audio (prosody) | Truer to delivery | No prosody from recognition; unreliable across languages | Revisit with owned models (gap b) |
| No affect conveyed at all | Simplest and fully private | The physician loses what a human interpreter would pass on | Rashod wants affect carried |
| Put the phrase on the controller only | Keeps affect fully private | The physician is looking at the patient, not the laptop, which is why the voice carried it | Spoken is the point |

## Consequences

- **Positive**: affect survives the tone failure; a single voice is simpler and more predictable; everything stays checkable with the mocked model.
- **Negative**: affect is now audible in the room and readable in the translation text; the physician hears a model's guess about how the patient feels; the phrase must be reviewed in five languages' reporting frames before any real use.
- **Risks and mitigations**: a wrong or over-read phrase could mislead the physician, mitigated by hedged wording, the plain default, and the controller label still showing the model's read; a phrase could drift into meaning, mitigated by the frame-only rule and the existing checks.

## Implementation

The `affect-in-words` OpenSpec change, with IDR-006 for the mechanics.
It amends, and does not supersede, MDD-005 decisions 2 and 3, IDR-005's voice delivery, and ADR-010's tone-by-emotion rule.
Code carries `@implements MDD-006: Affect in words`.

## Review Notes

- 2026-11-16, Claude (agent): Drafted from rashodkorala's direction in session.
  Awaiting human review; do not implement until accepted.
  No existing record's status has been changed; whether MDD-005, IDR-005, or ADR-010 are amended by annotation or superseded is the project lead's decision.
- 2026-11-16, rashodkorala: Accepted in session ("Accept both"), together with IDR-006.
  Recorded by Claude (agent) at rashodkorala's explicit request.
  His answers to the design's Open Questions: (1) the affect phrase stays visible in the caption translation text, so spoken and shown text are the same and there is no public and private text split; (2) for patient and companion turns the phrase is driven by `emotion`, not `manner`; (3) certainty steadiness in the voice is removed too, so certainty is carried by the words only; (4) interpreter lines do not keep a separate warm delivery and use the same single constant delivery as turn relays, so there is one delivery everywhere.
  He also decided that MDD-005, IDR-005, and ADR-010 are amended by reference and not superseded; their status stays accepted.
