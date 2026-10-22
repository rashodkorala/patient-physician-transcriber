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
    - "status is readback_required whenever a physician turn has critical values"
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
  "status": "final | readback_required | escalated",
  "attempts": 1
}
```
`confidence` is 0 to 1. `criticalValues[].matched` is computed deterministically, not by the model.

## Evolution Strategy

Additive fields are non-breaking. Enum changes or removals need a superseding CDR.

## Testing Requirements

Pydantic validation tests with fixtures; a TypeScript type test against a JSON fixture; a test that a mismatched dose yields `matched: false` and `status: readback_required`.

## Consequences

- **Positive**: screens and tests share one shape.
- **Negative**: model output must be coerced into the schema.
- **Risks and mitigations**: structured outputs and retry on validation failure.

## Implementation

Code carries `@contract TurnResult` and `@implements CDR-002: Turn result schema`.

## Review Notes

- 2026-10-22, Claude (agent): Drafted as a proposal. Awaiting human review; do not implement until accepted.
- 2026-10-22, rashodkorala: Accepted in decision review. Recorded by Claude (agent) at rashodkorala's explicit request.
