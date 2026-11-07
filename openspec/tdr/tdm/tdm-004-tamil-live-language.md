---
id: tdm-004
title: "Tamil is the chosen live language, alongside Punjabi and French, spoken by ElevenLabs"
status: accepted
date: 2026-11-06
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: human
category: temporary
related_decisions: [mdd-003, tdm-003, adr-010, adr-005, adr-002, cdr-002]
related_specs: [demo-consultation-flow, interpreter-voice]
related_changes: [demo-night-mvp, mediator-voice]
expires: 2026-11-20
ai_context:
  implementation_priorities:
    - "Tamil (ta-LK) is selectable without test mode, like Punjabi and French; Sinhala stays test-only under TDM-003"
    - "Tamil relays are spoken by ElevenLabs (ADR-010) with language_code ta; Azure ta-LK stays the fallback"
    - "The critical value check reads Tamil units, number words, and frequencies, so correct Tamil relays are not blocked"
  framework_hints:
    - "Tamil units take case endings (மாதங்களில்), so they are matched as stems in server/critical_values.py"
    - "Test script: docs/test-script-tamil.md (type 2 diabetes)"
  validation_rules:
    - "A Tamil dose, number, or frequency that differs from the source is still blocked (CDR-002)"
    - "With test mode off, Tamil is selectable and Sinhala shows as coming soon"
    - "Tamil content (glossary, tone guide, empathy, interpreter lines) still needs a native speaker's review before it is relied on"
affects: [server/contracts.py, server/critical_values.py, web/lib/languages.ts, web/components/Controller.tsx]
implementation_refs: [server/contracts.py, server/critical_values.py, server/main.py, web/lib/languages.ts, web/components/Controller.tsx]
test_refs: [server/tests/test_critical_values.py, server/tests/test_visit_channel.py, web/e2e/test-languages.mjs]
---

# TDM-004: Tamil is the chosen live language, alongside Punjabi and French, spoken by ElevenLabs

## Summary

Tamil is the language the project works in for now.
It leaves test mode and becomes selectable on every start, next to Punjabi and French, and its relays are spoken by ElevenLabs.

## Context

- **Situation**: on 6 November 2026 the project lead chose Tamil as the language to finish the project with, and ElevenLabs as its voice.
  Tamil already ran end to end in test mode (TDM-003), with a knowledge base, interpreter lines, and an ElevenLabs voice.
- **Why temporary**: the project lead said "for now"; which languages go further is a product decision after demo night (MDD-001).
- **Review or expiry trigger**: expires 2026-11-20, the day after demo night, or earlier if the project lead picks another language.

## Decision

Tamil (`ta-LK`, Sri Lankan Tamil) is a live patient language with English as the physician language.
It no longer needs `TEST_LANGUAGES=on`; Sinhala still does, and TDM-003 is otherwise unchanged.
Punjabi and French stay live, so MDD-003's stage pairs are kept and Tamil is added to them.
Tamil relays and interpreter lines are spoken by ElevenLabs `eleven_v4` with `language_code` `ta` (ADR-010), with the Azure `ta-LK` voice as the fallback.
The critical value check reads Tamil units, number words, and frequencies, as it does for Punjabi and French (CDR-002).

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Tamil only, Punjabi and French to "coming soon" | One language to polish | Loses the two languages already tested live | Project lead chose to keep them |
| Tamil as the default on `/control` | One less click | Hides the language choice the demo shows | Project lead chose to keep the picker as it is |
| Keep Tamil test-only | No record change | Cannot finish the project in Tamil | Not what the project lead asked |

## Consequences

- **Positive**: the project can be finished and shown in Tamil; Tamil gets the same safety checks as the other languages.
- **Negative**: Tamil knowledge base content and interpreter lines are still drafts awaiting a native speaker.
- **Risks and mitigations**: unreviewed Tamil wording, mitigated by the Tamil test script run with a speaker; Tamil number words read wrongly, mitigated by reading them only before a unit and only when they add up largest first.

## Implementation

`TEST_LANGUAGES` in `server/contracts.py` keeps only Sinhala; `web/lib/languages.ts` lists Tamil as live; the critical value check gains Tamil units, numbers, and frequencies.
The `mediator-voice` change carries the Tamil tasks.

## Review Notes

- 2026-11-06, rashodkorala: Decided in session: "we will use tamil as the chosen language for now. let's use eleven labs", then chose Tamil live with Punjabi and French kept, and asked for the record to be written as accepted. Recorded by Claude (agent) at rashodkorala's explicit request.
