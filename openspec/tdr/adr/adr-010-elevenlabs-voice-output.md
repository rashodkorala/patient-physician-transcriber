---
id: adr-010
title: "Voice output: ElevenLabs Eleven v4 replaces OpenAI text-to-speech; Azure stays fallback"
status: accepted
date: 2026-11-03
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: architecture
related_decisions: [adr-009, adr-005, mdd-004, cdr-003]
related_specs: [interpreter-voice]
related_changes: [mediator-voice]
ai_context:
  implementation_priorities:
    - "Speak verified relays and interpreter lines with ElevenLabs eleven_v4 through the server's speak-by-id endpoint (CDR-003)"
    - "Carry the turn's emotion and certainty as delivery: an audio tag such as [measured] or [warm] plus a stability setting, from a fixed reviewed table"
    - "Pass language_code (pa, fr, en) on every request"
  framework_hints:
    - "Python SDK `elevenlabs` (AsyncElevenLabs) on the server; ELEVENLABS_API_KEY from the environment, loaded from .env.local by scripts/dev.sh"
    - "HTTP streaming (text_to_speech.stream) so audio starts before synthesis ends; measure eleven_v4 against eleven_v4_turbo for latency"
    - "Azure neural voices stay behind the same speak() interface as the per-language fallback"
  validation_rules:
    - "The ElevenLabs key never reaches the browser"
    - "Only a final turn, a confirmed read-back, or an interpreter line is ever synthesised"
    - "Audio tags are added by the server from the fixed table, never written by a model, and never change the words"
    - "Chosen only if the blind listening test (mediator-voice task 0.4) prefers it for Punjabi and French"
affects: [web/lib/speech.ts, server/main.py, scripts/dev.sh]
implementation_refs: [server/voice.py, server/main.py, server/config.py, web/lib/speech.ts, web/components/Controller.tsx]
test_refs: [server/tests/test_voice.py, web/e2e/server-voice.mjs]
---

# ADR-010: Voice output: ElevenLabs Eleven v4 replaces OpenAI text-to-speech; Azure stays fallback

## Summary

The server speaks with ElevenLabs `eleven_v4` instead of OpenAI `gpt-4o-mini-tts`.
Everything else in ADR-009 stands: the server gates what is spoken, audio streams to the browser, and Azure stays the fallback.

## Context

- **Technical drivers**: checked on 3 November 2026, OpenAI's text-to-speech guide does not list Punjabi and says `gpt-4o-mini-tts` shuts down on 6 January 2027, pointing to its Realtime API, which ADR-009 rejected because speech could start before the safety checks.
  ElevenLabs lists Punjabi and French for `eleven_v4`.
- **Quality attributes**: natural delivery, Punjabi quality, latency.
- **Constraints**: prototype; vendor data-processing terms are a production question, not a factor here (project lead, 3 November 2026).

## Decision

Synthesis on the server uses ElevenLabs `eleven_v4` with `language_code` and a voice kept for the whole visit.
Tone follows the turn's emotion and certainty through a small reviewed table of audio tags and stability values.
If `eleven_v4` streaming is too slow for the latency target, `eleven_v4_turbo` is measured next.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Keep OpenAI `gpt-4o-mini-tts` (ADR-009) | Plain-language tone instructions | No listed Punjabi; shuts down January 2027 | Not viable past the prototype, and Punjabi is unproven |
| OpenAI Realtime | Natural, supported going forward | Speech-to-speech; checks cannot run before speaking | Unsafe (as in ADR-009) |
| Azure neural voices only | Already built, low latency | Judged not natural enough | Does not meet MDD-004 |

## Consequences

- **Positive**: Punjabi listed; expressive delivery; a supported model.
- **Negative**: tone is steered by tags and stability rather than a sentence, so the mapping needs tuning; Eleven v4 is still described as under active development.
- **Risks and mitigations**: tag-following is "not perfect yet" per ElevenLabs, mitigated by the listening test and Azure fallback; latency, mitigated by streaming and the turbo model.

## Implementation

The `mediator-voice` change, task group 3, with "OpenAI" read as "ElevenLabs" in tasks 3.1 to 3.4.

## Review Notes

- 2026-11-03, Claude (agent): Drafted at rashodkorala's request for an ElevenLabs server voice. Awaiting human review; do not implement until accepted.
  If accepted, ADR-009 moves to superseded.
- 2026-11-03, rashodkorala: Accepted in session. Recorded by Claude (agent) at rashodkorala's explicit request.
- 2026-11-06, rashodkorala: ADR-009 is now superseded by this record. Recorded by Claude (agent) at rashodkorala's explicit request.
