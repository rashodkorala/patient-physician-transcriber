# Tasks

## 0. Human decision review gate

TDRs: CDR-004

- [x] 0.1 Project lead reviews CDR-004 (interpreter voice playback on the visit channel) and sets it to accepted or rejected; verify `python3 scripts/check_tdr.py` no longer lists CDR-004 as awaiting review
- [x] 0.2 Project lead adds `orb-speaking-state` to `related_changes` of ADR-001, ADR-007, CDR-001, CDR-003, and EDR-002, or drafts replacements; verify each record lists the change

## 1. Playback on the visit channel

TDRs: CDR-004, CDR-001, CDR-003, ADR-007, EDR-002

- [x] 1.1 Add `voice.started`, `voice.ended`, `voice.speaking`, and `visit.state.speaking` to `server/contracts.py` and `web/lib/contracts.ts`, add both commands to `CONTROLLER_COMMANDS`, and regenerate `web/lib/generated/`; verify contract tests and `npm run check:contracts` pass
  - 2026-11-06: contract tests for both fixtures, the speaking validator, id limits, and a state without `speaking`; `npm run check:contracts` passes.
- [x] 1.2 Handle both commands in `server/main.py` against the existing speak gate, with one speaking state on the in-memory visit; verify pytest covers refused ids (blocked, escalated, rejected, unsettled, unknown, wrong language), a repeated start, and a stale end
  - 2026-11-06: `tests/test_visit_channel.py` covers every refused id, a repeated start, a stale end, and back-to-back interpreter lines.
- [x] 1.3 Clear the state when the starting controller disconnects and after 60 seconds without an end, with an injectable clock; verify pytest covers both, and that a screen connecting mid-speech receives `speaking` in `visit.state`
  - 2026-11-06: the ceiling is injectable (`create_app(voice_ceiling_s=...)`, 0.05 s in the test) rather than a clock; disconnect and mid-speech snapshot tests pass.
- [x] 1.4 Verify pytest shows a screen's `voice.started` and `voice.ended` have no effect and produce no event
  - 2026-11-06: `test_screen_cannot_report_voice_playback` passes; full server suite 173 passed.

## 2. Controller reports playback

TDRs: CDR-004, CDR-003

Also depends on the continuous-listening change's speaking signal; add its decision record's id to this line once it is on the main branch.
Built by the continuous-listening work, which owns `web/lib/speech.ts` and `web/components/Controller.tsx`.

- [x] 2.1 Send `voice.started` and `voice.ended` with the speech id and language from the shared speaking signal, on every end path (finished, failed, stopped); verify with the fake-model stack that each spoken relay and interpreter line produces exactly one start and one end, including when the voice fails (2026-11-07: a Sinhala relay spoken by Azure, three introduction lines spoken by ElevenLabs, and a voice that errors mid-playback each gave exactly one start and one end, accepted by the server, with /screen ending silent; mapping unit-tested in `web/lib/speaking.test.mjs`)

## 3. Speaking state on the shared screen

TDRs: CDR-004, ADR-001

- [x] 3.1 Add a Speaking mode to the orb (both speakers' colours, rings moving out, still under reduced motion); verify screenshots at 1440, 960, and 390 pixels and a reduced-motion check
  - 2026-11-07: screenshots of all five states at 1440, Ready and Speaking at 960 and 390 in light and dark, no overflow; under reduced motion no animation runs and Speaking keeps a still ring.
- [x] 3.2 Drive it in `web/components/SharedScreen.tsx` from `voice.speaking` and `visit.state.speaking`, as its own Interpreter row above any pending turn (so the voice is never shown under the next speaker's label), and hide the ready line while speaking; verify an e2e script with a controller socket shows Speaking on start, leaves it on end, and leaves it when the controller disconnects
  - 2026-11-07: `node e2e/orb-speaking.mjs http://localhost:3200 8200` passes: refused id never shown, Speaking while playing, a screen joining mid-speech, cleared on end and on controller disconnect. Placement changed from "precedence over the pending turn" during build; see the change's review.
- [x] 3.3 Run `node e2e/week1.mjs` against the fake-model stack; verify it still passes
  - 2026-11-07: `node e2e/week1.mjs http://localhost:3200` passes on the fake-model stack.
