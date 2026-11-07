# Tasks

## 0. Human decision review gate

TDRs: MDD-004, ADR-009, CDR-003

- [x] 0.1 Project lead reviews MDD-004 (mediator voice) and sets it to accepted or rejected; verify `python3 scripts/check_tdr.py` no longer lists MDD-004 as awaiting review
- [x] 0.2 Project lead reviews CDR-003 (names and interpreter lines); verify it is accepted or replaced in `openspec/tdr/index.md`
- [x] 0.3 Project lead adds `mediator-voice` to `related_changes` of ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007, CDR-001, CDR-002, EDR-002, and IDR-001, or drafts replacements; verify each record lists the change
- [ ] 0.4 Run a blind listening test of OpenAI, ElevenLabs, and the current Azure voices (clips from `uv run python scripts/voice_samples.py`) with the Punjabi and French speakers on ten sample relays each; record the chosen voice per language and the verdict in docs/voice-test.md
- [x] 0.5 Project lead decides ADR-009 using the listening test; if accepted, notes on ADR-005 that its synthesis half is replaced; verify `python3 scripts/check_tdr.py` shows no pending records for this change (2026-11-03: accepted by the project lead before the listening test; 0.4 still picks the voice per language)

## 1. Names on the visit channel

TDRs: CDR-001, CDR-003, ADR-007, EDR-002

- [x] 1.1 Add `visit.set_names`, `visit.names`, and the `visit.state` name and introduction fields to `server/contracts.py` and `web/lib/contracts.ts`, and regenerate `web/lib/generated/`; verify contract tests and `npm run check:contracts` pass
- [x] 1.2 Store names in the in-memory visit and handle `visit.set_names` in `server/main.py`, with trimming, a 60 character limit, and no digits; verify pytest covers valid, too long, and mid-visit changes
- [x] 1.3 Add a name field and a saved default physician name on `/control`, sent when a visit opens; verify an e2e script shows the saved default applied to a new visit after reload (2026-11-03: `node e2e/names.mjs` passes against the fake-model stack)
- [ ] 1.4 Show speaker names on `/screen` captions; verify on the TV layout at 3 metres that names do not wrap or crowd the Gurmukhi line (code done 2026-11-03; `node e2e/names.mjs` checks names on /screen captions at 1920 by 1080; TV check pending)

## 2. Reported-speech relays and introduction

TDRs: MDD-004, ADR-002, ADR-004, ADR-006, CDR-002, CDR-003, EDR-002

- [x] 2.1 Add the mediator rules and name tags to the translate instructions in `server/graph/turn_graph.py`; verify mocked-LLM tests check the tags and fallbacks for physician, patient, and companion
- [ ] 2.2 Tell the tone check the reporting frame is expected; verify the speaker-rated tone set still passes and a frame-only relay is not escalated (code done 2026-11-03: tone check accepts the frame and checks meaning; mocked tests pass; speaker-rated tone set pending, as in demo-night-mvp task 2.7)
- [ ] 2.3 Run the demo-script lines through the live model in both directions; verify every critical value still matches and the native speakers rate the relays as faithful and natural in docs/voice-test.md (live run 2026-11-03 recorded in docs/voice-test.md: relays correct, 3 Punjabi turns blocked by the critical value check not reading Punjabi number words; native speaker ratings pending)
- [ ] 2.4 Write the interpreter's introduction and name-question lines per language in the i18n content with native speaker review; verify each line has a reviewer noted (drafts in `server/kb/content/interpreter/` 2026-11-03, all `reviewer: pending`; Punjabi lines avoid the interpreter's gender, to check against the chosen voice)
- [x] 2.5 Build the introduction flow (`visit.start_introduction`, `visit.name_reply`, confirm and reject, skip known names, skip entirely); verify pytest covers each path and an e2e script runs it from `/control` (2026-11-03: 7 channel tests in `tests/test_visit_channel.py`; `node e2e/introduction.mjs` passes on a fresh fake-model stack)
- [ ] 2.6 Add name extraction from a spoken reply with the tone-check model; verify mocked tests and five recorded replies per language propose the right name (mocked tests pass; 15 typed replies (5 per language) all read correctly with the live model on 2026-11-03, see docs/voice-test.md; replies spoken through recognition pending)

## 3. Interpreter voice

TDRs: ADR-010, ADR-005, CDR-003, EDR-002

- [x] 3.1 Add `GET /api/speech/{id}` that streams OpenAI speech for final turns, confirmed read-backs, and interpreter lines, and returns 404 otherwise; verify pytest covers blocked, escalated, rejected, unsettled, and unknown ids
  - Built with ElevenLabs per ADR-010 (`server/voice.py`, `server/main.py`); `server/tests/test_voice.py` covers every case.
    Interpreter lines take `?language=`; 503 means "speak with Azure instead" (no key, no voice for the language, or a vendor failure).
    Requests are limited to two at a time, the free plan's limit, found live as a 429.
- [x] 3.2 Build the emotion and certainty to voice instruction table; verify a unit test covers every emotion and certainty value
  - An audio tag and a stability value per emotion, steadier for high certainty (`EMOTION_DELIVERY`, `CERTAINTY_STEADINESS`); the tags still need review with the tone guides and the listening test.
- [x] 3.3 Switch `speak()` in `web/lib/speech.ts` to play the streamed audio, with Azure as the per-language fallback; verify the fallback by disabling the OpenAI key and speaking a turn
  - Verified live with `web/e2e/server-voice.mjs`: `punjabi` plays every line and a turn from the server with no Azure synthesis; `sinhala` gets a 503 and Azure speaks the turn.
    The no-key case is covered by `test_no_server_voice_means_the_browser_uses_azure`.
- [x] 3.4 Keep the OpenAI key server-only; verify a grep of the built web bundle finds no key and `/api/speech-token` returns only Azure tokens
  - 4 November 2026: the ElevenLabs key is in none of `web/.next` (dev build), the web source, or the served `/control` page; `/api/speech-token` is unchanged.
- [ ] 3.5 Log speech start in the latency CSV; verify the median release-to-audio time is under 3 seconds over the demo lines on the laptop
  - Speech start is logged as before. One live typed turn: caption to audio 891 ms, server 3.4 s, so the median over the demo lines with push-to-talk is still to measure.

## 4. End-to-end check

TDRs: MDD-004, ADR-010, CDR-003, EDR-002

- [ ] 4.1 Run a full Punjabi visit and a full French visit with the native speakers: introduction, names, five turns each way, one read-back, one blocked dose; verify the blocked dose is never spoken and record the run in docs/voice-test.md

## 5. Tamil as the live language

TDRs: TDM-004, ADR-010, CDR-002, EDR-002

- [x] 5.1 Record the project lead's choice of Tamil with ElevenLabs; verify `python3 scripts/check_tdr.py` passes with TDM-004 accepted (6 November 2026)
- [x] 5.2 Make Tamil selectable without test mode, keeping Sinhala test-only; verify pytest and `node e2e/test-languages.mjs off|on` pass
  - 6 November 2026: 148 pytest tests pass; both e2e modes pass against a fresh fake-model stack, and a Tamil visit relays with the Tamil glossary term on /screen.
- [x] 5.3 Teach the critical value check Tamil units (as stems, since Tamil adds case endings), number words, and frequencies; verify the Tamil test script lines no longer block correct relays
  - Before: 3 of 10 correct Tamil relays blocked (7.3, 7.5, 3.3). After: 0 of 11 blocked, every dose, number, and frequency matched in Tamil script (see docs/voice-test.md).
- [x] 5.4 Speak Tamil with ElevenLabs; verify a relay and an interpreter line stream audio
  - 6 November 2026: relay 7.3 first audio 1.2 s, introduction line 0.7 s, with `language_code` `ta`.
- [ ] 5.5 Tamil speaker reviews the glossary, tone guide, empathy phrases, and interpreter lines (all `reviewer: pending`), and rates the ElevenLabs Tamil voice against Azure `ta-LK-SaranyaNeural` in the listening test (0.4)
- [ ] 5.6 Run `docs/test-script-tamil.md` in full with the Tamil speaker, spoken through recognition, and record it in its test log

## Workflow follow-up

- Fill `implementation_refs` and `test_refs` in MDD-004, ADR-009, and CDR-003, then archive the change after review.
