---
id: adr-005
title: "Speech: Azure Speech primary, Google Speech backup"
status: accepted
date: 2026-10-22
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: architecture
related_decisions: [adr-001]
related_specs: []
related_changes: [demo-night-mvp, mediator-voice]
ai_context:
  implementation_priorities:
    - "Recognise pa-IN, fr-CA, en-CA; speak with neural voices in each"
  framework_hints:
    - "Azure Speech JS SDK in the browser with server-minted short-lived tokens"
    - "Google Cloud Speech and TTS as fallback"
  validation_rules:
    - "Speech keys never reach the browser"
    - "Measure recognition accuracy with the Punjabi speaker in week 1"
affects: [web/lib/speech.ts, server/speech_token.py]
implementation_refs: []
test_refs: []
---

# ADR-005: Speech: Azure Speech primary, Google Speech backup

## Summary

Use Azure Speech for recognition and synthesis in Punjabi, Canadian French, and English, with Google Cloud as the backup if Punjabi quality disappoints.

## Context

- **Technical drivers**: needs Punjabi and Canadian French recognition and natural voices.
- **Quality attributes**: accuracy, latency.
- **Constraints**: keys available for Azure, Google, and OpenAI.

## Decision

Browser uses the Azure Speech SDK with tokens minted by the server. Week 1 includes a Punjabi accuracy test with the team's speaker; if it fails, switch to Google behind the same front-end interface.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Browser Web Speech API | Free | Patchy Punjabi support and voices | Unreliable for demo |
| OpenAI Whisper and TTS | Strong recognition | Punjabi voice quality uncertain; batch latency | Kept as tertiary option |

## Consequences

- **Positive**: one vendor covers both directions.
- **Negative**: vendor lock for the demo.
- **Risks and mitigations**: speech access behind one module so the vendor can switch.

## Implementation

`web/lib/speech.ts` wraps recognise and speak; `server/speech_token.py` mints tokens.

## Review Notes

- 2026-10-22, Claude (agent): Drafted as a proposal. Awaiting human review; do not implement until accepted.
- 2026-10-22, rashodkorala: Accepted in decision review. Recorded by Claude (agent) at rashodkorala's explicit request. Condition: the week 1 Punjabi accuracy test (demo-night-mvp task 1.4) decides whether to switch to Google Speech.
- 2026-11-03, rashodkorala: Extended to the mediator-voice change. Recorded by Claude (agent) at rashodkorala's explicit request. Its synthesis half is replaced by ADR-009 for mediator-voice; recognition is unchanged.
