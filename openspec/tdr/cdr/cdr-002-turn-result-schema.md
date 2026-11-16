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
related_changes: [demo-night-mvp, mediator-voice, trust-across-the-barrier, affect-in-words]
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
    - "status is unclear when confidence is still below the threshold after one retry and the speaker has had fewer than two consecutive unclear turns before this one; unclear turns are never spoken and never shown as a translation"
    - "status is escalated only for the third consecutive unclear turn from the same speaker (reason low_confidence) or a tone failure after one retry (reason tone_failure)"
    - "the unclear streak is kept per speaker; a final or read-back-confirmed turn resets it and a blocked turn does not change it"
    - "precedence when several rows apply: blocked, escalated, unclear, readback_required, final"
    - "TurnResult is controller-only; shared screens receive TurnCaption, which never carries emotion, certainty, back-translation, or an unspoken translation"
affects: [server/graph/turn_state.py, web/lib/contracts.ts]
implementation_refs: []
test_refs: []
---

# CDR-002: Turn result schema

## Summary

Defines two shapes for one translated utterance: the full `TurnResult` (controller and server only) and the public `TurnCaption` projection sent to shared screens.

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
| Confidence still below threshold after one retry, fewer than two consecutive unclear turns from this speaker | `unclear` | Never | Original and a say-it-again notice in both languages; the interpreter asks aloud in the speaker's language |
| Third consecutive unclear turn from the same speaker, or a tone failure after one retry | `escalated` | No | Marked uncertain; human interpreter offered (ADR-003) with reason `low_confidence` or `tone_failure` (CDR-001) |
| Physician rejects highlighted values at read-back | (turn discarded, via `turn.readback_reject` in CDR-001) | No | Speaker asked to repeat (covers recognition errors) |

When more than one row applies, the first in this order wins: `blocked`, then `escalated`, then `unclear`, then `readback_required`, then `final`. A turn whose critical values match but whose confidence or tone check still fails is `escalated` or `unclear`: it is never read back or spoken.

The server keeps an unclear streak per speaker (patient, physician, companion). The first and second consecutive unclear turns from the same speaker are `unclear`; the third is `escalated` with reason `low_confidence`. Any `final` or read-back-confirmed turn from that speaker resets the streak, and blocked turns do not change it. A tone failure after one retry escalates at once, because repeating does not repair a meaning drift.

Shared screens (`/screen`, `/review`) only ever render a translation after it has been spoken. A `blocked`, `unclear`, or `escalated` turn shows the original text and a notice, never its translation or translated values.

## Data Schemas

**TurnResult** (full; server and physician controller only, via `turn.analysis` in CDR-001):
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
  "status": "final | readback_required | blocked | escalated | unclear",
  "attempts": 1,
  "unclearStreak": 0
}
```
`unclearStreak` is an integer, controller only: the speaker's unclear streak after this turn (0 after a `final` or read-back-confirmed turn). `confidence` is 0 to 1. `criticalValues[].matched` is computed deterministically, not by the model. `attempts` is 1 or 2 (one retry at most). When `status` is `blocked`, at least one `criticalValues[].matched` is `false`; otherwise every entry is `true`.

**TurnCaption** (public projection; every screen, via `turn.result` in CDR-001):
```json
{
  "turnId": "string",
  "speaker": "patient | physician | companion",
  "sourceLanguage": "pa-IN | fr-CA | en-CA",
  "targetLanguage": "pa-IN | fr-CA | en-CA",
  "sourceText": "string",
  "status": "final | blocked | escalated | unclear",
  "translation": "string | null",
  "toneLabel": "respectful | reassuring | empathetic | neutral | null",
  "glossaryUsed": [{ "term": "string", "translation": "string", "explanation": "string" }],
  "criticalValues": [{ "kind": "string", "source": "string", "translated": "string" }],
  "readbackConfirmed": false
}
```
A `TurnCaption` is emitted once a turn is settled: after it is spoken (`final`, with `readbackConfirmed: true` if the physician confirmed values), or when it is `blocked`, `unclear`, or `escalated`. For `blocked`, `unclear`, and `escalated`, `translation` and `toneLabel` are `null` and `criticalValues` is empty. It never contains `emotion`, `certainty`, `backTranslation`, `confidence`, or `toneTags` values outside the four register labels.

## Evolution Strategy

Additive fields are non-breaking. Before the contract is first implemented (`implementation_refs` empty), it may be amended in place with a dated review note from the decision owner. After that, enum changes or removals need a superseding CDR.

## Testing Requirements

Pydantic validation tests with fixtures and a TypeScript type test against a JSON fixture, plus:
- a dose mismatched on the first attempt and matched on the retry yields `attempts: 2`, all `matched: true`, and `status: readback_required` for a physician turn;
- a dose mismatched on both attempts yields `matched: false` and `status: blocked`;
- a `blocked` result never reaches speech synthesis and never emits `interpreter.escalation`;
- a confidence failure on both attempts yields `status: unclear` and no escalation; two consecutive unclear turns from one speaker followed by a third yields `unclear`, `unclear`, `escalated`, the last with an escalation of reason `low_confidence`;
- a `final` (or read-back-confirmed) turn from the same speaker between two unclear turns resets the streak, so the next unclear turn is `unclear`, not `escalated`;
- a tone-only failure on both attempts yields `status: escalated` and reason `tone_failure` at once;
- a physician turn whose dose matches but whose tone check fails twice yields `status: escalated`, never `readback_required`;
- the `TurnCaption` for a `blocked`, `unclear`, or `escalated` turn has `translation: null` and no translated values, and no `TurnCaption` ever carries `emotion`, `certainty`, or `backTranslation`.

## Consequences

- **Positive**: screens and tests share one shape.
- **Negative**: model output must be coerced into the schema.
- **Risks and mitigations**: structured outputs and retry on validation failure.

## Implementation

Code carries `@contract TurnResult` or `@contract TurnCaption` and `@implements CDR-002: Turn result schema`.

## Review Notes

- 2026-10-22, Claude (agent): Drafted as a proposal. Awaiting human review; do not implement until accepted.
- 2026-10-22, rashodkorala: Accepted in decision review. Recorded by Claude (agent) at rashodkorala's explicit request.
- 2026-10-22, rashodkorala: Amended in place before implementation: added `blocked` status and the single outcome table, so a critical value still mismatched after one re-translation is never spoken and the speaker is asked to repeat (previously a mismatch could reach `readback_required`). Recorded by Claude (agent) at rashodkorala's explicit request.
- 2026-10-22, rashodkorala: Amended to reference the new `tone_failure` escalation reason in CDR-001. Recorded by Claude (agent) at rashodkorala's explicit request.
- 2026-10-22, rashodkorala: Amended in place before implementation: status precedence (blocked, escalated, readback_required, final); public `TurnCaption` projection so emotion, certainty, back-translations, and unspoken or blocked translations never reach shared screens. Recorded by Claude (agent) at rashodkorala's explicit request.
- 2026-11-03, rashodkorala: Extended to the mediator-voice change. Recorded by Claude (agent) at rashodkorala's explicit request.
- 2026-11-10, rashodkorala: Extended to the trust-across-the-barrier change under the blanket authorisation given in session (see MDD-005). Recorded by Claude (agent) at rashodkorala's explicit request.
- 2026-11-10, rashodkorala: Additive amendment by CDR-008 and IDR-005: `TurnResult` gains `manner` (every turn) and `TurnCaption` gains `manner` (a final physician turn only, otherwise null). `toneLabel` stays in the shape; screens now show the manner label instead. Recorded by Claude (agent) under the blanket authorisation given in session (see MDD-005).
- 2026-11-12, rashodkorala: Amended by ADR-003: `TurnResult.status` and `TurnCaption.status` gain `unclear`, `TurnResult` gains the controller-only `unclearStreak`, `escalated` for low confidence now needs a third consecutive unclear turn from the same speaker, and the precedence becomes blocked, escalated, unclear, readback_required, final. The enum addition is made under the blanket authorisation given in session (see MDD-005) rather than a superseding record. Recorded by Claude (agent) at rashodkorala's explicit request.
