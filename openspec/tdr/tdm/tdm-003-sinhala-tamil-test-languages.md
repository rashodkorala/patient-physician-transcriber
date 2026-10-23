---
id: tdm-003
title: "Sinhala and Tamil as test-only languages before demo night"
status: proposed
date: 2026-10-23
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: temporary
related_decisions: [mdd-003, adr-002, adr-005, adr-006, idr-002]
related_specs: [demo-consultation-flow]
related_changes: [demo-night-mvp]
expires: 2026-11-19
ai_context:
  implementation_priorities:
    - "Sinhala and Tamil selectable only when the presenter enables test mode"
    - "Collect evidence on recognition, translation, tone, and latency in two lower-resource languages"
  framework_hints:
    - "Same speech provider rules as ADR-005 (Azure first, Google if a language fails the check)"
    - "Knowledge base content for en-si and en-ta written with native speakers (ADR-002, IDR-002)"
    - "Test scripts: docs/test-script-tamil.md and docs/test-script-sinhala.md"
  validation_rules:
    - "Test mode is never enabled on stage"
    - "With test mode off, Sinhala and Tamil show as coming soon"
    - "Results are recorded in each test script's test log and in docs/language-benchmark.md"
affects: []
implementation_refs: []
test_refs: []
---

# TDM-003: Sinhala and Tamil as test-only languages before demo night

## Summary

Before demo night, Sinhala and Tamil can be selected in a presenter-enabled test mode so the team can run full test scripts in both languages. They are never used on stage, and MDD-003's stage scope (Punjabi and French) is unchanged.

## Context

- **Situation**: the project lead wants to see how the system copes with Sinhala and Tamil before demo night; native speakers for both are available.
- **Why temporary**: test-only access ends at demo night; whether either language goes further is a product decision after the demo.
- **Review or expiry trigger**: expires 2026-11-19.

## Decision

Add a presenter-enabled test mode in which Sinhala and Tamil are selectable as patient languages, with English as the physician language. Run `docs/test-script-tamil.md` (type 2 diabetes) and `docs/test-script-sinhala.md` (high blood pressure) in full, and record results in their test logs and `docs/language-benchmark.md`. Speech, translation, and knowledge base work for these languages follows ADR-005, ADR-006, ADR-002, and IDR-002; if a language needs a different speech vendor than Azure, the Google backup in ADR-005 applies. Stage behaviour, MDD-003 scope, and the demo script are unchanged.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Paper-only scripts | No build work | Learns nothing about real recognition or translation quality | Defeats the purpose of testing |
| Add both to the stage | Bigger demo | Amends MDD-003 and adds stage risk in the weakest languages | Not requested; stage stays Punjabi and French |
| Test one language only | Less work | Misses the comparison between two lower-resource languages | Speakers for both are available |

## Consequences

- **Positive**: real evidence on lower-resource languages before demo night and for the roadmap's language tiers.
- **Negative**: extra knowledge base content and speaker time; a test mode switch in the demo build.
- **Risks and mitigations**: test mode is presenter-only and off by default; a stage checklist item confirms it is off; expiry at demo night.

## Implementation

Test mode flag on the controller (presenter mode); language list honours it. Knowledge base files `server/kb/glossary/en-si.yaml`, `en-ta.yaml`, `tone/si.md`, `tone/ta.md`, `empathy/si.yaml`, `empathy/ta.yaml`, and condition explainers for type 2 diabetes and high blood pressure.

## Review Notes

- 2026-10-23, Claude (agent): Drafted as a proposal. Awaiting human review; do not implement until accepted.
