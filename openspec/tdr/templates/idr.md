---
id: idr-NNN
title: "[Short decision title]"
status: proposed              # proposed | accepted | rejected | superseded | deprecated
date: YYYY-MM-DD
authors: ["[name or agent]"]
reviewers: ["[human reviewer]"]
decision_owner: "[Component owner]"
proposed_by: human            # human | agent
category: implementation
related_decisions: []         # e.g. [mdd-001, adr-002]
related_specs: []             # OpenSpec capability paths
related_changes: []           # OpenSpec change names
ai_context:
  implementation_priorities: []
  framework_hints: []
  validation_rules: []
affects: []                   # optional: components or files governed
implementation_refs: []       # optional: filled in after implementation
test_refs: []                 # optional: tests that verify this decision
---

# IDR-NNN: [Short decision title]

> Implementation Decision Record. Only a human may set `status: accepted`.

## Summary

One or two sentences: what was decided.

## Context

- **Feature or component**:
- **Technical requirements**:
- **Constraints**:

## Decision

What we will do, stated precisely enough for an agent to implement.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|

## Consequences

- **Positive**:
- **Negative**:
- **Risks and mitigations**:

## Implementation

How this shows up in code, tests, and specs. Code governed by this record carries `@implements IDR-NNN: [title]`.

## Review Notes

- YYYY-MM-DD, [reviewer]: [comment or decision]
