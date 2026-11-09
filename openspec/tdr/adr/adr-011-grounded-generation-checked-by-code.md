---
id: adr-011
title: "Explain-back, note, and summary: frozen sources, model proposes, code checks provenance and values"
status: proposed
date: 2026-11-08
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: architecture
related_decisions: [mdd-001, mdd-003, adr-002, adr-004, adr-006, cdr-002, cdr-005, cdr-006, cdr-007, idr-003]
related_specs: [demo-consultation-flow]
related_changes: [demo-night-mvp]
ai_context:
  implementation_priorities:
    - "Build every generation from one frozen source set taken from the record chain, never from live mutable state"
    - "The model proposes structured output with source ids; code validates ids, derives allowed tags, and compares every number"
    - "One retry with the problems pinned in the prompt, then fail or refuse; never patch model text silently"
  framework_hints:
    - "Plain LangChain single-pass chains with structured outputs validated by Pydantic (ADR-004, ADR-006)"
    - "server/chains/{explain_back,note,summary}.py; source freezing in one shared module"
    - "Reuse server/critical_values.py quantities() and frequencies() for every deterministic comparison"
    - "Model ids from server/config.py only (ADR-006): Opus 5.5 for note and summary, Sonnet 5.5 for explain-back"
    - "The fake model (server/fake_model.py) returns fixture outputs, including wrong ones, for tests (EDR-002)"
  validation_rules:
    - "Blocked, escalated, rejected, and discarded turns are never sources; their translations are never sent to these models"
    - "Emotion, certainty, back-translation, nudges, and demo injection or tamper state are never sent to these models"
    - "A stated tag is allowed only when every source has that speaker; otherwise code downgrades it to ai_inference"
    - "Code-decided explain-back items keep the code's outcome whatever the model says"
    - "Every critical value in a summary must equal one in its sources as the patient heard it, and every read-back-confirmed dose must appear"
affects: [server/chains/, server/critical_values.py, server/config.py, server/fake_model.py]
implementation_refs: []
test_refs: []
---

# ADR-011: Explain-back, note, and summary: frozen sources, model proposes, code checks provenance and values

> Architectural Decision Record. Only a human may set `status: accepted`.

## Summary

The explain-back comparison, the clinical note, and the patient summary are each one model call over a frozen set of source turns taken from the record chain.
The model returns structured output that cites source ids; code then checks every citation, decides which provenance tag each sentence may carry, and compares every number, dose, frequency, and medication against the sources, with one retry before the output is refused.
This applies to the live product principle that every statement is traceable or marked as AI inference (MDD-001) and to CDR-002's rule that critical values are compared by code, not by the model.

## Context

- **Technical drivers**: design.md says these are plain LangChain single-pass chains with structured outputs (ADR-004) and that the summary passes a deterministic dose check, but no record says what the chains may read, how a provenance tag is justified, how explain-back decides "missed", or which model runs explain-back.
  ADR-006 names Opus 5.5 for the note and summary and is silent on explain-back.
- **Quality attributes**: clinical safety (no changed dose reaches the patient), honesty of provenance, privacy of the physician-only analysis, and repeatable tests with a mocked model (EDR-002).
- **Constraints**: demo scope (MDD-003); in-memory state (ADR-007); the record is an append-only hash chain (IDR-003, CDR-006); explain-back runs while the patient waits, so it must be quick.

## Decision

### 1. One frozen source set

When a chain starts (CDR-005 `explainback.start` freezes the plan; CDR-007 `note.generate` and `summary.generate` freeze at their command), the server takes a snapshot:

- the chain head hash (`basedOnHead` or `planHeadHash`);
- every turn that settled as spoken (`final`, or read-back confirmed), at its effective version (latest applied correction, CDR-006), with turn id, version, speaker, names, source language and text, target language and spoken translation, and the public critical values, plus `readbackConfirmed`;
- the interpreter's own lines (CDR-003), which may be cited only as `interpreter_stated`;
- the ids of blocked and escalated turns, listed as gaps without their translations.

Nothing else is sent to the model: no emotion, certainty, back-translation, confidence, empathy nudges, injection or tamper state, and no unspoken translation.
The chain does not hold those fields either (CDR-006), so the snapshot can be built from chain entries alone.

### 2. Model proposes, code checks

Each chain asks the model for structured output that cites `SourceRef`s (CDR-007).
Code then validates:

| Check | Rule | On failure |
|---|---|---|
| Source exists | Every cited id and version is in the frozen set | Retry once with the bad ids pinned, then fail |
| At least one source | Every note sentence, summary sentence, and explain-back item cites one or more sources | Retry once, then fail |
| Tag allowed | `patient_stated` only if every source is a patient turn; `physician_stated` only if every source is a physician turn; `companion_stated` only if every source is a companion turn; `interpreter_stated` only if every source is an interpreter line; `ai_inference` always allowed | Downgrade the tag to `ai_inference` and list it in `tagDowngrades`; never upgrade a tag |
| Values in note sentences | Every quantity and frequency code finds in a stated sentence (via `critical_values.py`) equals one in its cited sources; an `ai_inference` sentence may not introduce a dose or frequency absent from all sources | Retry once with the mismatches pinned, then fail |
| Values in the summary | See section 4 | Retry once, then refuse |

Code never rewrites model text to make a check pass.

### 3. Explain-back comparison

- **Code items.** For every critical value in the frozen physician turns of kind `dose`, `frequency`, `medication`, `number`, or `date`, code makes one plan item with `decidedBy: "code"`.
  It extracts values from each explanation turn's original text (patient language) and its spoken translation (physician language) with `critical_values.py`.
  The item is `matched` if the same normalised value is found, `contradicted` if a different value of the same kind is found where it is the only value of that kind or is tied to the same medication, and `missed` otherwise.
- **Model items.** The model reads the frozen plan and the explanation and returns the non-numeric instructions (`instruction`, `warning`, `follow_up`), each with an outcome and evidence turn ids.
  It also sees the code items so it does not duplicate them, but its view of their outcome is discarded.
- **Model.** Explain-back runs on Sonnet 5.5, the live-turn model, because the patient and physician wait for it.
  ADR-006 does not cover explain-back; this record decides it, and ADR-006 is not amended.
  The id comes from `server/config.py`.

### 4. Summary value check

After the model writes the summary in the patient's language (Opus 5.5, ADR-006), code:

1. extracts every quantity, frequency, and known medication name from the summary text in that language;
2. builds the expected set in the patient's language: for physician turns, the translated values as spoken to the patient; for patient turns, the source values;
3. marks a value `changed` if no expected value of the same kind and unit equals it, and `unsupported` if it is a number with no source at all;
4. marks a read-back-confirmed dose or its frequency `missing` if the summary does not contain it.

Any mismatch, including a `missing` confirmed dose or frequency, triggers one retry with the expected values pinned; if any mismatch remains, the summary is refused (CDR-007) and never published, spoken, or chained.
A summary that passes is chained (CDR-006).
A summary in a language whose units `critical_values.py` does not know is refused, as live doses already are (task 6.3).

### 5. Note

The note runs on Opus 5.5 (ADR-006) in English with fixed section headings (CDR-007).
The physician remains its author (MDD-001): the note is a checked draft, not a signed record.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Trust the model's tags and values | One call, no code | A model can tag inference as patient-stated or change a dose; nothing would catch it | Breaks MDD-001's traceability and CDR-002's code-checked values |
| Derive tags from sources only, no model tag | Fully deterministic | Every sentence that merges a patient and a physician turn becomes inference, even when it only restates one; the model's view is useful to downgrade from | Model tag kept, code may only downgrade |
| Feed the full `TurnResult` (emotion, certainty, back-translation) | Richer note | Leaks physician-only analysis into artefacts and the patient's summary; back-translations are not what anyone said | Public, spoken content only |
| Generate from live state instead of a frozen snapshot | Simpler | A correction or new turn mid-generation gives sources that no longer match citations | Frozen snapshot with `basedOnHead` and a stale flag |
| Explain-back entirely by the model | Handles paraphrase | A lenient model could call a missed frequency matched, the exact case task 3.4 must flag | Code decides every critical value item |
| Explain-back on Opus 5.5 | Best judgement | Slower while two people wait in the room | Sonnet 5.5; revisit after rehearsal timings |
| Fix wrong summary values by substitution | Always produces a summary | Silently edited text can break grammar or meaning in Punjabi or Tamil; hides model drift | Retry, then refuse |

## Consequences

- **Positive**: provenance is honest by construction, a changed or dropped dose cannot reach the patient's summary, and a missed frequency is always flagged; all three are testable offline with the fake model.
- **Negative**: more code than a single prompt; strict checks can refuse a good summary that paraphrases a number in words the extractor does not know.
- **Risks and mitigations**: false refusals on stage, mitigated by extending `critical_values.py` word lists with the native speakers during rehearsal, the retry with pinned values, and replay mode (TDM-001).
  Explain-back paraphrase of a frequency ("morning and night") may read as missed; the physician sees the evidence and can re-ask, and the word lists grow from rehearsal logs.

## Implementation

`server/chains/explain_back.py`, `server/chains/note.py`, and `server/chains/summary.py`, with one shared source-freezing module and the deterministic checks reusing `server/critical_values.py`.
Code carries `@implements ADR-011: Explain-back, note, and summary: frozen sources, model proposes, code checks provenance and values`.
Tests with the fake model cover each row of the check table, the explain-back code items (a missed frequency, a contradicted frequency, a model that says matched for a missed value), the summary checks (changed, missing, unsupported), and that no request to the model contains emotion, certainty, back-translation, or a blocked or escalated translation.

## Review Notes

- 2026-11-08, Claude (agent): Drafted as a proposal for the supervising session, for demo-night-mvp tasks 3.4, 3.6, and 3.7. Awaiting human review; do not implement until accepted.
- 2026-11-09, Claude (agent): Revised to state rashodkorala's answers, relayed by the supervising session: explain-back runs on Sonnet 5.5, decided here with no ADR-006 edit, and a summary that leaves out a confirmed dose is refused. Still proposed; awaiting human review.
