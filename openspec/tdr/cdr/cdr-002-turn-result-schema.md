---
id: cdr-002
title: "Turn result schema"
status: accepted
date: 2026-10-22
authors: ["Claude (agent)"]
reviewers: ["rashodkorala", "front-end owner", "back-end owner"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: api-contract
related_decisions: [adr-002, adr-004, cdr-001]
related_specs: []
related_changes: [demo-night-mvp]
ai_context:
  implementation_priorities:
    - "Single shape for every translated turn"
  framework_hints:
    - "Pydantic model TurnResult on the server; matching TypeScript type in web/lib/contracts.ts"
  validation_rules:
    - "criticalValues.matched is deterministic"
    - "status is readback_required only when a physician turn has critical values and every one matches"
    - "status is blocked when any critical value is still unmatched after one re-translation"
    - "blocked turns are never spoken and never trigger automatic escalation"
    - "status is escalated only for confidence or tone failures after one retry"
affects: [server/graph/turn_state.py, web/lib/contracts.ts]
implementation_refs: []
test_refs: []
---

# CDR-002: Turn result schema

## Summary

Defines the TurnResult object for one translated utterance: translation, back-translation, tone, glossary terms used, critical values, confidence, and status.

## Context

- **Integration point**: turn graph output to every screen.
- **Related decisions**: ADR-002, ADR-004, CDR-001.
- **Requirements**: captions, tone labels, read-back, escalation.

## Decision

Adopt the schema below as TurnResult version 1.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Free-form text result | Easy | Screens cannot render tone or values reliably | Not structured |

## Contract Specification

Produced by the turn graph (ADR-004) for every utterance and carried in `turn.result`. Also returned by `POST /api/turns/{turnId}` for debugging.

Any verify failure triggers one retry, with mismatched critical values pinned in the prompt. The outcome after that is exactly one status:

| Verify result | Status | Spoken? | What the screens do |
|---|---|---|---|
| All critical values match, physician turn has critical values | `readback_required` | After physician confirms | Values highlighted in both languages; confirm or reject |
| All checks pass, no critical values needing read-back | `final` | Yes | Caption and speech |
| Critical value still mismatched after one re-translation | `blocked` | Never | Controller shows mismatched values; speaker asked to repeat or rephrase |
| Confidence or tone check still failing after one retry | `escalated` | No | Marked uncertain; human interpreter offered (ADR-003) with reason `low_confidence` or `tone_failure` (CDR-001) |
| Physician rejects highlighted values at read-back | (turn discarded, via `turn.readback_reject` in CDR-001) | No | Speaker asked to repeat (covers recognition errors) |

## Data Schemas

```json
{
  "turnId": "string",
  "speaker": "patient | physician | companion",
  "sourceLanguage": "pa-IN | fr-CA | en-CA",
  "targetLanguage": "pa-IN | fr-CA | en-CA",
  "sourceText": "string",
  "translation": "string",
  "backTranslation": "string",
  "toneTags": ["reassuring | respectful | empathetic | neutral | urgent | uncertain"],
  "emotion": "calm | worried | embarrassed | in_pain | relieved | confused",
  "certainty": "high | medium | low",
  "glossaryUsed": [{ "term": "string", "translation": "string", "explanation": "string" }],
  "criticalValues": [{ "kind": "dose | unit | frequency | date | number | medication", "source": "string", "translated": "string", "matched": true }],
  "confidence": 0.0,
  "status": "final | readback_required | blocked | escalated",
  "attempts": 1
}
```
`confidence` is 0 to 1. `criticalValues[].matched` is computed deterministically, not by the model. `attempts` is 1 or 2 (one retry at most). When `status` is `blocked`, at least one `criticalValues[].matched` is `false`; otherwise every entry is `true`.

## Evolution Strategy

Additive fields are non-breaking. Before the contract is first implemented (`implementation_refs` empty), it may be amended in place with a dated review note from the decision owner. After that, enum changes or removals need a superseding CDR.

## Testing Requirements

Pydantic validation tests with fixtures and a TypeScript type test against a JSON fixture, plus:
- a dose mismatched on the first attempt and matched on the retry yields `attempts: 2`, all `matched: true`, and `status: readback_required` for a physician turn;
- a dose mismatched on both attempts yields `matched: false` and `status: blocked`;
- a `blocked` result never reaches speech synthesis and never emits `interpreter.escalation`;
- a confidence failure on both attempts yields `status: escalated` and an escalation with reason `low_confidence`; a tone-only failure on both attempts yields `status: escalated` and reason `tone_failure`.

## Consequences

- **Positive**: screens and tests share one shape.
- **Negative**: model output must be coerced into the schema.
- **Risks and mitigations**: structured outputs and retry on validation failure.

## Implementation

Code carries `@contract TurnResult` and `@implements CDR-002: Turn result schema`.

## Review Notes

- 2026-10-22, Claude (agent): Drafted as a proposal. Awaiting human review; do not implement until accepted.
- 2026-10-22, rashodkorala: Accepted in decision review. Recorded by Claude (agent) at rashodkorala's explicit request.
- 2026-10-22, rashodkorala: Amended in place before implementation: added `blocked` status and the single outcome table, so a critical value still mismatched after one re-translation is never spoken and the speaker is asked to repeat (previously a mismatch could reach `readback_required`). Recorded by Claude (agent) at rashodkorala's explicit request.
- 2026-10-22, rashodkorala: Amended to reference the new `tone_failure` escalation reason in CDR-001. Recorded by Claude (agent) at rashodkorala's explicit request.
