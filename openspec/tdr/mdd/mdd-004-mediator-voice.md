---
id: mdd-004
title: "Mediator voice: the interpreter speaks as a person between the parties, in reported speech"
status: accepted
date: 2026-11-03
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: strategy
related_decisions: [mdd-001, adr-002, adr-003, adr-009]
related_specs: [mediator-interpretation, visit-introduction]
related_changes: [mediator-voice, trust-across-the-barrier, affect-in-words]
ai_context:
  implementation_priorities:
    - "Interpret each turn in reported speech that names the speaker, for example 'Dr. Thomas is saying you should take this medicine 2 times a day after every meal'"
    - "Apply it in both directions: the physician hears 'The patient is saying ...' or the patient's name"
    - "Open each visit with a short spoken introduction by the interpreter, in both languages"
    - "Use names set at visit setup; a clinic or physician default name skips the question"
  framework_hints:
    - "Change the translation instructions, not the graph shape; the tone check is told the reporting frame is expected"
  validation_rules:
    - "Numbers, doses, units, frequencies, dates, and medication names stay exact; critical value checks still apply"
    - "Plain wording may be used, but no instruction is softened, added, or dropped"
    - "Certainty and emotion are kept, as today (ADR-002)"
    - "The interpreter never adds its own clinical advice or answers on the physician's behalf"
affects: [server/graph/turn_graph.py]
implementation_refs: []
test_refs: []
---

# MDD-004: Mediator voice: the interpreter speaks as a person between the parties, in reported speech

## Summary

The interpreter acts as a person standing between the physician and the patient.
It relays each turn in reported speech that names the speaker, in plain and warm language, instead of repeating the speaker's words in the first person.

## Context

- **Business Context**: today the interpreter repeats what was said word for word in the speaker's voice, which reads and sounds robotic.
  Rashod wants it to feel like a real interpreter sitting next to both people.
- **Strategic Drivers**: building tone and empathy into the interpreter itself; making the voice clearly a go-between, not the physician.
- **Constraints**: professional interpreting standards (IMIA, NCIHC) teach first-person interpreting because third person can blur who "he" and "you" are.
  This decision departs from that norm on purpose, so names must be used to keep the roles clear.

## Decision

1. Each turn is interpreted in reported speech that names the speaker ("Dr. Thomas is saying ...", "Harpreet is saying ...").
   Without a name, the interpreter says "your doctor" or "the patient".
2. The interpreter may use plain, everyday wording, but every instruction, number, dose, frequency, date, and medication name is kept exactly, and nothing is softened, added, or dropped.
3. It applies in both directions.
4. At the start of a visit the interpreter introduces itself in both languages and asks for any name not already known: first the physician's, then the patient's.
5. A physician or clinic can set the physician's name once as a default for all visits, so the question is skipped.
6. The interpreter never gives its own medical advice and never answers a question on someone else's behalf; it relays.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Keep first-person interpreting | Matches professional interpreter norms; fewest words | Sounds robotic; listener may think the machine is the doctor | Does not meet the product direction |
| Reported speech only from physician to patient | Physician gets precise first-person text | Two styles in one visit; less natural for the physician | Consistency matters more; captions still show the original |
| Free paraphrase and summary | Most conversational | Risk of meaning drift and dropped instructions | Unsafe for clinical content |

## Consequences

- **Positive**: more human and empathetic; clear who is speaking; a natural place for warmth and reassurance.
- **Negative**: slightly longer spoken turns; departs from interpreting norms clinicians may know.
- **Risks and mitigations**: meaning drift, mitigated by the unchanged critical value checks and a tone check told to accept the reporting frame; name mix-ups, mitigated by asking for and confirming names at the start.

## Implementation

The `mediator-voice` OpenSpec change: translation instructions, tone check instructions, visit setup names and defaults, and the opening introduction.

## Review Notes

- 2026-11-03, Claude (agent): Drafted as a proposal from rashodkorala's direction in session. Awaiting human review; do not implement until accepted.
- 2026-11-03, rashodkorala: Accepted in session. Recorded by Claude (agent) at rashodkorala's explicit request.
- 2026-11-10, rashodkorala: Extended to the trust-across-the-barrier change under the blanket authorisation given in session (see MDD-005). Recorded by Claude (agent) at rashodkorala's explicit request.
