---
id: idr-007
title: "Remove the separate model tone check for demo turns"
status: accepted
date: 2026-11-17
authors: ["Codex (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala"
proposed_by: agent
category: implementation
related_decisions: [adr-003, adr-004, adr-006, cdr-002, idr-006]
related_specs: [demo-consultation-flow, manner-in-relay]
related_changes: [demo-night-mvp, affect-in-words]
ai_context:
  implementation_priorities:
    - "Remove the separate tone_check model call from live demo turn verification"
    - "Keep deterministic critical-value checks, physician read-back, confidence routing, and code-based translation checks"
  framework_hints:
    - "Update the verification node and reconcile the affected specs and turn outcomes before coding"
  validation_rules:
    - "An ordinary bilingual turn issues no tone_check request"
    - "A deliberately mismatched dose still blocks and a matched physician dose still requires confirmation"
    - "Deterministic translation failures still retry and route through the existing failure path"
affects: [server/graph/turn_graph.py, server/tests/test_turn_graph.py]
implementation_refs: []
test_refs: []
---

# IDR-007: Remove the separate model tone check for demo turns

## Summary

Remove the additional model request in live turn verification to reduce demo latency.

## Context

The separate model request checks meaning, certainty, and warmth by comparing the original with the back-translation.
It runs before a turn can be released and may contribute to retry latency.

## Decision

Remove the separate model check for demo turns.
Keep deterministic checks for critical values, back-translation language, reporting frames, copied text, and guessed gender.
Keep the existing dose read-back and confidence paths.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Keep synchronous model verification | Retains separate review | Keeps the additional request on the critical path | The requested demo change removes that request |

## Consequences

A successful turn will require one fewer model request.
Meaning, certainty, and warmth will no longer receive a separate model review.

## Implementation

Update the turn graph's verification node and its tests after review.
Verify French-to-English release, dose blocking, and dose confirmation in the demo flow.

## Review Notes

- 2026-11-17, rashodkorala: Accepted. Recorded by Codex at rashodkorala’s explicit request.

- 2026-11-17, Codex: Drafted for review in response to the request to remove the tone check.
