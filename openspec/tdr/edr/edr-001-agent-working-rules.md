---
id: edr-001
title: "Agent working rules: TDR gates, annotations, commits, and reviews"
status: accepted
date: 2026-10-22
authors: ["rashodkorala"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: human
category: engineering-practice
related_decisions: [mdd-002]
related_specs: []
related_changes: [add-multilingual-medical-consultation, demo-night-mvp]
ai_context:
  implementation_priorities:
    - "Read MDD, then ADR, then CDR, EDR, and IDR before implementing"
    - "Use each TDR's ai_context in prompts"
  framework_hints:
    - "/opsx:apply for implementation"
    - "scripts/check_tdr.py before every commit"
  validation_rules:
    - "Never implement a task whose TDRs are not accepted"
    - "Never decide a TDR status; record a status change only for an explicit verdict a named human gave in the same session and asked the agent to record"
    - "Stop and draft a proposed TDR when a new decision is needed"
affects: []
implementation_refs: []
test_refs: []
---

# EDR-001: Agent working rules: TDR gates, annotations, commits, and reviews

## Summary

Rules every AI agent and human follows when building: decision gates, code annotations, commit messages, and pull request review.

## Context

- **Current state**: agents implement OpenSpec tasks via /opsx:apply.
- **Pain points**: agents otherwise make silent architectural choices.
- **Quality goals**: every line of code traces to an accepted decision and a spec requirement.

## Decision

1. Before a task: confirm every TDR listed for its task group is accepted (`python3 scripts/check_tdr.py`).
2. New decision needed (architecture, contract, vendor, data, safety, privacy): copy the matching template from `openspec/tdr/templates/`, fill it with `status: proposed` and `proposed_by: agent`, add it to `openspec/tdr/index.md`, and stop for human review.
3. Code annotations: `@implements <TDR-ID>: <title>`, `@contract <endpoint or schema>` for CDR-governed code, `@see <path>`.
4. Tests name the TDR they verify (for example `test_turn_result_schema_cdr_002`).
5. Commits reference TDR ids: `feat: live turn graph (ADR-004, CDR-002)`.
6. Pull requests use the template checklist; a human reviews and merges.
7. Recording human verdicts: an agent never decides a TDR status. It may change a status (accepted, rejected, superseded, or deprecated) only to record a verdict that a named human gave explicitly in the same session and asked the agent to record. The record's Review Notes then state the human, the date, and "Recorded by <agent> at <human>'s explicit request", and the commit message names the human decider.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Informal review | Fast | Decisions drift silently | Defeats DDSE |

## Consequences

- **Positive**: traceable, reviewable agent output.
- **Negative**: a little overhead per task.
- **Risks and mitigations**: the checker script automates most checks.

## Implementation

Documented in `AGENTS.md`, enforced by `openspec/config.yaml` apply guidance and `scripts/check_tdr.py`.

## Review Notes

- 2026-10-22, rashodkorala: Accepted by the project lead in the planning conversation.
- 2026-10-22, rashodkorala: Amended to add rule 7 (agents may record an explicit human verdict). Recorded by Claude (agent) at rashodkorala's explicit request.
