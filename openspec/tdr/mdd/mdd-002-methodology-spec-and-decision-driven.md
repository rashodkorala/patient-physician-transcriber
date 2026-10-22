---
id: mdd-002
title: "Methodology: spec-driven (OpenSpec) plus decision-driven (DDSE) with human gates"
status: accepted
date: 2026-10-22
authors: ["rashodkorala"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: human
category: strategy
related_decisions: [edr-001]
related_specs: []
related_changes: [add-multilingual-medical-consultation, demo-night-mvp]
ai_context:
  implementation_priorities:
    - "Specs say what; TDRs say why and how"
    - "Humans accept decisions; agents implement within them"
  framework_hints:
    - "OpenSpec 1.14.3 CLI and /opsx commands"
    - "DDSE v1.1 record types: MDD, ADR, CDR, EDR, IDR, TDM"
  validation_rules:
    - "No task starts while a TDR it depends on is not accepted"
    - "Agents never set a TDR to accepted"
affects: []
implementation_refs: []
test_refs: []
---

# MDD-002: Methodology: spec-driven (OpenSpec) plus decision-driven (DDSE) with human gates

## Summary

All work follows OpenSpec for behaviour and DDSE v1.1 for decisions, so AI agents can build while humans decide and review.

## Context

- **Business Context**: a small team building fast with AI agents for demo night on 19 November 2026.
- **Strategic Drivers**: keep humans in control of decisions while agents do most of the implementation.
- **Constraints**: lightweight enough for a four-week build.

## Decision

Use OpenSpec changes (proposal, specs, design, tasks) as the source of truth for behaviour, and DDSE Technical Decision Records in `openspec/tdr/` as the source of truth for decisions. Designs cite TDR ids, tasks list them, and code carries `@implements` annotations. Lifecycle: Decision Required, Decision In Progress (proposed), Decision Approved (accepted by a human), Implementation.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| OpenSpec only | Less paperwork | Decisions get buried in design.md and agents make silent choices | Weak human control |
| DDSE only | Strong governance | No behaviour contracts or task tracking | Loses spec-driven workflow |
| Plain ADRs (Nygard) | Familiar | No contract or implementation levels, no AI context | DDSE is a superset suited to agents |

## Consequences

- **Positive**: every choice is visible and reviewable; agents get structured context.
- **Negative**: overhead per decision.
- **Risks and mitigations**: keep records short; TDMs for temporary demo choices.

## Implementation

`openspec/config.yaml` rules, `AGENTS.md`, `openspec/tdr/README.md`, and `scripts/check_tdr.py` enforce this. Working rules for agents are in EDR-001.

## Review Notes

- 2026-10-22, rashodkorala: Accepted by the project lead in the planning conversation.
