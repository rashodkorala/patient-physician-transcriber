---
id: tdm-003
title: "Sinhala and Tamil as test-only languages before demo night"
status: accepted
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
    - "Sinhala and Tamil selectable only when the server is started in test mode (start-up setting, off by default, restart to change)"
    - "Controller shows a test-mode banner while test mode is on; shared and review screens do not"
    - "Collect evidence on recognition, translation, tone, and latency in two lower-resource languages"
  framework_hints:
    - "Same speech provider rules as ADR-005 (Azure first, Google if a language fails the check)"
    - "Knowledge base content for en-si and en-ta written with native speakers (ADR-002, IDR-002)"
    - "Test scripts: docs/test-script-tamil.md and docs/test-script-sinhala.md"
  validation_rules:
    - "Test mode is never enabled on stage; there is no runtime toggle"
    - "Test runs use only the fictional script content; speakers agree beforehand"
    - "No audio from test runs is retained; replay logs from test runs are deleted once the run summary is written"
    - "With test mode off, Sinhala and Tamil show as coming soon"
    - "Results are recorded in each test script's test log and in docs/language-benchmark.md"
affects: []
implementation_refs: []
test_refs: []
---

# TDM-003: Sinhala and Tamil as test-only languages before demo night

## Summary

Before demo night, Sinhala and Tamil can be selected when the server is started in test mode, so the team can run full test scripts in both languages. Test mode is a start-up setting, off by default, and cannot be switched on during a session. They are never used on stage, and MDD-003's stage scope (Punjabi and French) is unchanged.

## Context

- **Situation**: the project lead wants to see how the system copes with Sinhala and Tamil before demo night; native speakers for both are available.
- **Why temporary**: test-only access ends at demo night; whether either language goes further is a product decision after the demo.
- **Review or expiry trigger**: expires 2026-11-19.

## Decision

Add a test mode, chosen only when the server starts (for example `TEST_LANGUAGES=on`), off by default, and changeable only by restarting; there is no runtime toggle, so it cannot be switched on during the stage show, and CDR-001 is unchanged. In test mode Sinhala and Tamil are selectable as patient languages, with English as the physician language, and the controller shows a test-mode banner.

Tester privacy: test runs use only the fictional content of the test scripts; each speaker agrees before taking part; no audio from test runs is retained, and replay logs from test runs are deleted once the run summary is written. Only the filled-in test logs are kept. Run `docs/test-script-tamil.md` (type 2 diabetes) and `docs/test-script-sinhala.md` (high blood pressure) in full, and record results in their test logs and `docs/language-benchmark.md`. Speech, translation, and knowledge base work for these languages follows ADR-005, ADR-006, ADR-002, and IDR-002; if a language needs a different speech vendor than Azure, the Google backup in ADR-005 applies. Stage behaviour, MDD-003 scope, and the demo script are unchanged.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Paper-only scripts | No build work | Learns nothing about real recognition or translation quality | Defeats the purpose of testing |
| Add both to the stage | Bigger demo | Amends MDD-003 and adds stage risk in the weakest languages | Not requested; stage stays Punjabi and French |
| Test one language only | Less work | Misses the comparison between two lower-resource languages | Speakers for both are available |

## Consequences

- **Positive**: real evidence on lower-resource languages before demo night and for the roadmap's language tiers.
- **Negative**: extra knowledge base content and speaker time; a test mode switch in the demo build.
- **Risks and mitigations**: test mode is a start-up setting, off by default, with no runtime toggle; the stage checklist confirms the server was started without it (no banner); testers' voices are not retained; expiry at demo night.

## Implementation

Start-up setting read by the server (for example `TEST_LANGUAGES=on`); the language list and the controller banner honour it; no command in CDR-001. Test-run replay logs are deleted after the summary. Knowledge base files `server/kb/glossary/en-si.yaml`, `en-ta.yaml`, `tone/si.md`, `tone/ta.md`, `empathy/si.yaml`, `empathy/ta.yaml`, and condition explainers for type 2 diabetes and high blood pressure.

## Review Notes

- 2026-10-23, Claude (agent): Drafted as a proposal. Awaiting human review; do not implement until accepted.
- 2026-10-24, rashodkorala: Accepted with clarifications: test mode is a server start-up setting (off by default, restart to change, no runtime toggle, no CDR-001 change); test runs use fictional content only, speakers agree beforehand, and no audio is retained. Recorded by Claude (agent) at rashodkorala's explicit request.
