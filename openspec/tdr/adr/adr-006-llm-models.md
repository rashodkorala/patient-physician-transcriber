---
id: adr-006
title: "LLM: Claude Sonnet 5.5 for live turns, Opus 5.5 for note and summary"
status: proposed
date: 2026-10-22
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: architecture
related_decisions: [adr-004]
related_specs: []
related_changes: [demo-night-mvp]
ai_context:
  implementation_priorities:
    - "Live turn calls must be fast"
    - "Note and summary favour quality over speed"
  framework_hints:
    - "Model ids: claude-sonnet-5-5 (live), claude-opus-5-5 (note, summary)"
    - "Consult the claude-api skill when writing model calls"
    - "Use structured outputs validated by Pydantic"
  validation_rules:
    - "Model ids live in one config module"
    - "No model id hard-coded in nodes or chains"
affects: [server/graph/, server/chains/]
implementation_refs: []
test_refs: []
---

# ADR-006: LLM: Claude Sonnet 5.5 for live turns, Opus 5.5 for note and summary

## Summary

Use Claude Sonnet 5.5 for the live analyse, translate, and verify steps and Claude Opus 5.5 for the clinical note and patient summary.

## Context

- **Technical drivers**: latency budget under 3 seconds per turn; high quality for the record.
- **Quality attributes**: accuracy in Punjabi and French.
- **Constraints**: Anthropic key available.

## Decision

Configure models in `server/config.py`. Use structured outputs for every call. Benchmark Punjabi turns in week 1 and revisit if latency or quality falls short.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| One model for everything | Simpler | Either too slow live or weaker for the note | Different needs |
| Haiku 5.5 for live turns | Fastest | Weaker Punjabi quality expected | Revisit only if latency fails |

## Consequences

- **Positive**: balanced speed and quality.
- **Negative**: two model behaviours to test.
- **Risks and mitigations**: model choice is configuration, easy to change.

## Implementation

`server/config.py` exposes model ids; nodes and chains import from it.

## Review Notes

- 2026-10-22, Claude (agent): Drafted as a proposal. Awaiting human review; do not implement until accepted.
