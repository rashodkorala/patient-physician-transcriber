---
id: edr-002
title: "Testing: pytest with mocked LLM, speaker-rated tone set, latency check"
status: proposed
date: 2026-10-22
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: engineering-practice
related_decisions: [mdd-003, adr-004]
related_specs: []
related_changes: [demo-night-mvp]
ai_context:
  implementation_priorities:
    - "Unit tests never call real AI services"
    - "Human ratings for tone quality"
  framework_hints:
    - "pytest for server; Vitest only if front-end logic grows"
    - "Fixtures in server/tests/fixtures/"
  validation_rules:
    - "Tests cover hash chain tampering, critical value matching, glossary retrieval, and turn graph branching"
affects: []
implementation_refs: []
test_refs: []
---

# EDR-002: Testing: pytest with mocked LLM, speaker-rated tone set, latency check

## Summary

Automated tests use mocked models; translation tone quality is checked by the Punjabi and French speakers on a fixed set of ten lines; latency is measured per turn.

## Context

- **Current state**: no code yet.
- **Pain points**: AI output is non-deterministic.
- **Quality goals**: reliable demo, measurable tone quality.

## Decision

pytest with a fake chat model for the turn graph (retry and escalate branches, glossary terms reach the prompt, critical values preserved). Deterministic tests for the hash chain and critical value matcher. A tone set of ten scripted physician lines (bad news, reassurance, sensitive questions) rated 1 to 5 by native speakers for accuracy, respect, and warmth each week. Latency logged for every turn; target under 3 seconds.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Live API tests in CI | Realistic | Slow, flaky, costly | Kept as a manual smoke test |

## Consequences

- **Positive**: fast tests plus real quality signal.
- **Negative**: human rating takes speaker time.
- **Risks and mitigations**: keep the tone set small.

## Implementation

`server/tests/`, `docs/tone-ratings.md` for weekly scores.

## Review Notes

- 2026-10-22, Claude (agent): Drafted as a proposal. Awaiting human review; do not implement until accepted.
