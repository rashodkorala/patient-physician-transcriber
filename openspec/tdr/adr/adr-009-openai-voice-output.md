---
id: adr-009
title: "Voice output: OpenAI text-to-speech with tone instructions; Azure keeps recognition"
status: accepted
date: 2026-11-03
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: architecture
related_decisions: [adr-005, mdd-004, adr-002]
related_specs: [interpreter-voice]
related_changes: [mediator-voice]
ai_context:
  implementation_priorities:
    - "Speak finished, verified translations with OpenAI gpt-4o-mini-tts"
    - "Pass the turn's emotion and certainty as the voice's instructions, so it sounds calm, warm, or serious as the speaker did"
    - "Stream audio from the server to the browser so speech starts quickly"
  framework_hints:
    - "Server endpoint calls OpenAI and streams audio; the browser plays it behind the existing speak() interface in web/lib/speech.ts"
    - "Azure Speech stays for recognition (ADR-005)"
  validation_rules:
    - "The OpenAI key never reaches the browser"
    - "Only a turn that passed its checks (final, or read back and confirmed) is ever sent for speech"
    - "Punjabi and Canadian French voices pass a listening test with the team's speakers before acceptance"
    - "Speech start latency is measured against the current Azure voices"
affects: [web/lib/speech.ts, server/main.py]
implementation_refs: []
test_refs: []
---

# ADR-009: Voice output: OpenAI text-to-speech with tone instructions; Azure keeps recognition

## Summary

Spoken output moves from Azure neural voices to OpenAI's `gpt-4o-mini-tts`, steered per turn by the emotion and certainty the translate step already reads.
Recognition stays on Azure Speech.

## Context

- **Technical drivers**: Rashod finds the Azure voices not good enough for a mediator that should sound like a person (MDD-004).
- **Quality attributes**: naturalness, expressed empathy, latency, Punjabi and French quality.
- **Constraints**: ADR-005 already holds OpenAI keys and lists OpenAI TTS as a tertiary option, held back because Punjabi voice quality was uncertain.

## Decision

The server calls OpenAI text-to-speech with the verified translation and an instruction built from the turn's emotion and certainty, and streams the audio to the browser.
The browser keeps one `speak()` interface, so the vendor stays switchable.
This replaces the synthesis half of ADR-005; its recognition half is unchanged.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Keep Azure neural voices | Already built; low latency | Judged not natural enough | Does not meet the product direction |
| OpenAI Realtime speech-to-speech agent | Most natural and conversational | Hears and speaks in one step, so critical value checks, read-back, and blocking cannot run before speech | Unsafe: a wrong dose could be spoken |
| ElevenLabs or similar | Very natural voices | New vendor, new DPA; Punjabi coverage unknown | Not needed if OpenAI passes the listening test |

## Consequences

- **Positive**: more human, expressive voice; empathy carried into how it sounds.
- **Negative**: one more network hop through the server; two speech vendors.
- **Risks and mitigations**: Punjabi quality, mitigated by the listening test gate and keeping Azure as fallback behind `speak()`; latency, mitigated by streaming and measured per ADR-005's latency logging.

## Implementation

The `mediator-voice` OpenSpec change: a server speech endpoint, a streamed audio player in `web/lib/speech.ts`, and tone instructions derived from the turn result.

## Review Notes

- 2026-11-03, Claude (agent): Drafted as a proposal from rashodkorala's direction in session. Awaiting human review; do not implement until accepted.
  If accepted, ADR-005 needs a human note that its synthesis half is replaced by this record.
- 2026-11-03, rashodkorala: Accepted in session. Recorded by Claude (agent) at rashodkorala's explicit request. Accepted before the Punjabi and French listening test; the test (mediator-voice task 0.4) still picks the voice per language, and Azure stays the fallback where OpenAI falls short.
- 2026-11-03, Claude (agent): ADR-010 (accepted) replaces this record's vendor choice with ElevenLabs. Whether this record becomes superseded is for the project lead to decide.
