---
id: idr-003
title: "SHA-256 hash chain for the record-verified badge"
status: accepted
date: 2026-10-22
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: implementation
related_decisions: [mdd-003]
related_specs: []
related_changes: [demo-night-mvp]
ai_context:
  implementation_priorities:
    - "Each segment and amendment is hashed with the previous hash"
  framework_hints:
    - "Python hashlib SHA-256 over canonical JSON"
  validation_rules:
    - "Altering or removing any entry breaks verification at that entry"
affects: [server/hash_chain.py]
implementation_refs: []
test_refs: []
---

# IDR-003: SHA-256 hash chain for the record-verified badge

## Summary

Each transcript segment and amendment is appended to a SHA-256 hash chain; the record screen shows 'verified' when the chain checks out and 'broken' when it does not.

## Context

- **Feature or component**: record-verified badge and tamper demo.
- **Technical requirements**: detect any change to past entries.
- **Constraints**: demo scope; no external anchoring.

## Decision

`server/hash_chain.py` keeps entries `{index, payload, prevHash, hash}` where hash is SHA-256 of canonical JSON of index, payload, and prevHash. Verification recomputes the chain and reports the first broken index. A hidden demo control alters one stored segment to show detection.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Blockchain or external ledger | Stronger | Cost and complexity | Out of scope for demo |

## Consequences

- **Positive**: simple, convincing integrity demo.
- **Negative**: no protection against replacing the whole chain.
- **Risks and mitigations**: external anchoring in the roadmap.

## Implementation

`server/hash_chain.py`; `record.integrity` event (CDR-001).

## Review Notes

- 2026-10-22, Claude (agent): Drafted as a proposal. Awaiting human review; do not implement until accepted.
- 2026-10-22, rashodkorala: Accepted in decision review. Recorded by Claude (agent) at rashodkorala's explicit request.
