---
id: cdr-NNN
title: "[Contract title]"
status: proposed              # proposed | accepted | rejected | superseded | deprecated
date: YYYY-MM-DD
authors: ["[name or agent]"]
reviewers: ["[project lead]", "[front-end owner]", "[back-end owner]"]
decision_owner: "[Project lead]"
proposed_by: human            # human | agent
category: api-contract
related_decisions: []         # MUST include the ADRs that set this contract's context
related_specs: []
related_changes: []
ai_context:
  implementation_priorities: []
  framework_hints: []
  validation_rules: []
affects: []
implementation_refs: []
test_refs: []
---

# CDR-NNN: [Contract title]

> Contract Decision Record. Every boundary between the screens and the server has one. Only a human may set `status: accepted`.

## Summary

What this contract covers and who produces and consumes it.

## Context

- **Integration point**:
- **Related decisions**:
- **Requirements**:

## Decision

The contract we commit to.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|

## Contract Specification

Endpoints, channels, or events, with direction and timing.

## Data Schemas

Exact field names, types, and required or optional status.

## Evolution Strategy

How the contract is versioned and how breaking changes are handled.

## Testing Requirements

Contract tests both sides must pass.

## Consequences

- **Positive**:
- **Negative**:
- **Risks and mitigations**:

## Implementation

Code governed by this record carries `@contract [endpoint or schema]` and `@implements CDR-NNN: [title]`.

## Review Notes

- YYYY-MM-DD, [reviewer]: [comment or decision]
