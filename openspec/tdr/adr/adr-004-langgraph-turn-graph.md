---
id: adr-004
title: "LangGraph for the per-turn translation graph; plain LangChain for single-pass chains"
status: accepted
date: 2026-10-22
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: architecture
related_decisions: [adr-001, adr-002, adr-003]
related_specs: []
related_changes: [demo-night-mvp]
ai_context:
  implementation_priorities:
    - "Per-turn graph: analyse, retrieve, translate, verify, retry once, then done, block, or escalate"
    - "Stream node status events to the screens"
  framework_hints:
    - "langgraph StateGraph with a TypedDict state for one turn"
    - "Model calls inside nodes and chains use the official anthropic Python SDK (structured outputs via messages.parse), not langchain-anthropic"
    - "Note, summary, and explain-back as plain LCEL chains"
  validation_rules:
    - "Graph holds only one turn's state; visit state stays in the server store"
    - "Verify node must check critical values deterministically"
affects: [server/graph/, server/chains/]
implementation_refs: []
test_refs: []
---

# ADR-004: LangGraph for the per-turn translation graph; plain LangChain for single-pass chains

## Summary

Use a LangGraph state graph for the live translation turn because it branches and loops, and plain LangChain chains for single-pass tasks.

## Context

- **Technical drivers**: verification can pass, retry, block, or escalate; status should stream to the UI.
- **Quality attributes**: clarity, testability, latency.
- **Constraints**: under 3 seconds per turn.

## Decision

Implement `server/graph/turn_graph.py` as a LangGraph `StateGraph` with nodes analyse, retrieve, translate, verify, block, and escalate, with conditional edges from verify: done (`final` or `readback_required`), retry once (any failure, with mismatched critical values pinned), block (critical value still mismatched), and escalate (confidence or tone still failing). Outcomes follow the status table in CDR-002. Use LCEL chains for note, summary, explain-back, and empathy nudges.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Plain LangChain LCEL only | Fewer dependencies | Retry, block, and escalate logic becomes ad-hoc code | Harder to follow and test |
| Hand-written Python pipeline | No framework | Loses streaming, tracing, and the user's chosen tooling | User asked for LangChain |
| Multi-agent graph | Flexible | Slower, less predictable | Overkill for one turn |

## Consequences

- **Positive**: explicit, testable control flow; per-node status.
- **Negative**: one more dependency to learn.
- **Risks and mitigations**: if latency is over budget, merge analyse into translate and run tone check asynchronously.

## Implementation

`server/graph/turn_state.py`, `nodes.py`, `turn_graph.py`; tests run the graph with a mocked model.

## Review Notes

- 2026-10-22, Claude (agent): Drafted as a proposal. Awaiting human review; do not implement until accepted.
- 2026-10-22, rashodkorala: Accepted in decision review. Recorded by Claude (agent) at rashodkorala's explicit request.
- 2026-10-22, rashodkorala: Amended: verify gains a block edge for critical value mismatches after one retry, aligned with CDR-002. Recorded by Claude (agent) at rashodkorala's explicit request.
- 2026-10-24, rashodkorala: Amended framework hint: LangGraph orchestrates the turn graph as decided, and every model call inside a node or chain uses the official anthropic SDK (as the week 1 path does), not langchain-anthropic. Recorded by Claude (agent) at rashodkorala's explicit request.
