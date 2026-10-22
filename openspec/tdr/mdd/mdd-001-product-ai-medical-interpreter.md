---
id: mdd-001
title: "Product: AI medical interpreter with a verified record, Canada first"
status: accepted
date: 2026-10-22
authors: ["rashodkorala"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: human
category: strategy
related_decisions: []
related_specs: []
related_changes: [add-multilingual-medical-consultation, demo-night-mvp]
ai_context:
  implementation_priorities:
    - "Language barrier between patient and physician is the core problem"
    - "Patient verifies the record in their own language"
  framework_hints:
    - "See docs/product-research.md for market and safety evidence"
  validation_rules:
    - "Every feature must help a patient and physician who do not share a language understand each other or trust the record"
affects: []
implementation_refs: []
test_refs: []
---

# MDD-001: Product: AI medical interpreter with a verified record, Canada first

## Summary

We are building an AI medical interpreter that also produces a bilingual record both parties verify, launching in Canada where immigration and linguistic diversity are high.

## Context

- **Business Context**: most recent immigrants to Canada have a mother tongue other than English or French; few physicians speak the most common non-official languages; family members, often children, interpret.
- **Strategic Drivers**: AI interpreters exist without verified records, and AI scribes exist without interpretation. Nobody combines them.
- **Constraints**: clinical safety varies by language; Canadian privacy law (PIPEDA, PHIPA, Quebec Law 25).

## Decision

Position the product as live medical interpretation plus a verified bilingual record. When patient and physician share a language the product runs in transcription-only mode, but the language barrier is the primary use case. Benchmarks: Abridge for the record, No Barrier and Care to Translate for interpretation.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Patient-trust AI scribe (same language) | Large existing market | Crowded; tone matters less when both share a language | User redirected focus to language barriers |
| Pure AI interpreter | Simpler | No record, no verification | Misses the trust differentiator |

## Consequences

- **Positive**: clear, underserved problem with a strong Canadian story.
- **Negative**: translation safety and latency become the main technical risks.
- **Risks and mitigations**: weaker languages are handled by human interpreter escalation (ADR-003).

## Implementation

Drives the OpenSpec changes `add-multilingual-medical-consultation` (roadmap) and `demo-night-mvp`.

## Review Notes

- 2026-10-22, rashodkorala: Accepted by the project lead in the planning conversation.
