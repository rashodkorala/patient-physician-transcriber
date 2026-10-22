# Design

## Context

Motivation and scope: see `proposal.md` and MDD-003. Behaviour: see `specs/demo-consultation-flow/spec.md`. Every technical choice below cites its TDR in `openspec/tdr/`. Choices marked *(proposed)* rely on a TDR that a human has not yet accepted; their tasks wait at group 0.

Constraints: one demo laptop plus a TV and optionally a phone on the same network; four weeks; native Punjabi and French speakers available for content review and rehearsals.

## Goals / Non-Goals

**Goals:**
- All nine demo beats working live for Punjabi and French, under 3 seconds per turn.
- Translation that keeps warmth, respect, and certainty, visibly.
- A demo that survives network failure.

**Non-Goals:**
- Production hardening, persistence, multi-visit support, or security beyond keeping keys server-side.

## Decisions

### Architecture (ADR-001)

```
 [TV  /screen]   [Laptop /control]   [Phone /review, /record]     web/ (Next.js)
        \               |                   /
         +----- WebSocket: CDR-001 events ----+
                         |
                 server/ (FastAPI)  -- visit_store (ADR-007, proposed)
                         |            -- hash_chain  (IDR-003, proposed)
                         |            -- speech_token (ADR-005, proposed)
              turn graph (ADR-004, proposed)
     analyse -> retrieve -> translate -> verify --+--> done
                              ^                   |
                              +--- retry once ----+--> escalate (ADR-003)
                         |
      knowledge base (ADR-002; retrieval per IDR-002, proposed)
      glossary | tone and culture | empathy phrases | condition explainers
                         |
      Claude models (ADR-006, proposed)
```

### Turn capture (IDR-001, proposed)
The controller has "Physician speaking" and "Patient speaking" buttons. The browser recognises speech (ADR-005) and sends `turn.submit` with speaker, language, text, and recognition confidence (CDR-001).

### Tone-aware turn graph (ADR-004, proposed)
- **analyse**: emotion, certainty, register, intent, and critical values (deterministic extractor for numbers and units, model for medication names).
- **retrieve**: glossary hits by exact and fuzzy match; tone, culture, and empathy entries for the listener's language by vector search (IDR-002).
- **translate**: model call with retrieved context and fixed rules: keep certainty, keep warmth, use the respectful register, explain jargon plainly, never change critical values.
- **verify**: back-translation, deterministic critical value comparison, and a tone check (certainty and warmth preserved). Pass: `final`, or `readback_required` for physician turns with critical values. Fail: retry once, then escalate.
- Each node emits `turn.status`; the result is a `TurnResult` (CDR-002).
- Empathy nudges (patient turns with worry, embarrassment, pain, or confusion) come from a separate chain using the empathy bank, sent only to the controller.

### Knowledge base (ADR-002)
`server/kb/`: `glossary/en-pa.yaml`, `glossary/en-fr.yaml`, `tone/{pa,fr,en}.md`, `empathy/{pa,fr,en}.yaml`, `conditions/*.md`. Content starts with the demo script's terms and lines and is reviewed by the native speakers.

### Single-pass chains (ADR-004, ADR-006)
Explain-back comparison, clinical note with provenance tags, and patient summary are plain LangChain chains with structured outputs. The summary passes a deterministic check that every number and dose matches the confirmed turns.

### State, integrity, and replay
- Visit state in memory, broadcast over WebSocket (ADR-007, proposed).
- SHA-256 hash chain over turns and amendments; hidden tamper control for the demo (IDR-003, proposed).
- Replay mode replays a recorded CDR-001 event log (TDM-001, proposed, expires 2026-11-20).

### Speech (ADR-005, proposed)
Azure Speech SDK in the browser with server-minted tokens; Google as backup. Week 1 includes a Punjabi accuracy test.

### Code layout
```
server/  main.py  config.py  contracts.py  visit_store.py  hash_chain.py  speech_token.py  replay.py
         graph/{turn_state,nodes,turn_graph}.py  chains/{empathy,explain_back,note,summary}.py
         kb/{index,retrieve}.py + content  tests/
web/     app/{page,control,screen,review,record}  lib/{speech,socket,contracts,languages}.ts  i18n/{en,fr,pa}.json
```

## Risks / Trade-offs

- [Latency over 3 seconds] → merge analyse into translate; run the tone check after the caption appears; keep retrieval local.
- [Punjabi recognition errors on stage] → week 1 test, rehearse the script with the speaker, Google as backup (ADR-005).
- [Tone check too strict causes retries] → tune during rehearsals using the tone set (EDR-002).
- [Venue network failure] → hotspot, then replay mode, then backup video (TDM-001).
- [Demo shortcuts leak into the product] → each shortcut is a demo-scoped TDR, revisited after demo night.

## Migration Plan

Not applicable. After demo night, archive TDM-001 and decide which demo TDRs carry into the roadmap change.

## Open Questions

- Accept or revise the eleven proposed TDRs (task group 0).
- Exact demo script lines and which medical condition to feature (affects knowledge base content only).
