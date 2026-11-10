# Tasks

## 0. Human decision review gate

TDRs: MDD-005, ADR-012, CDR-008, IDR-005

- [x] 0.1 Record rashodkorala's blanket authorisation of 2026-11-10 on MDD-005, ADR-012, CDR-008, and IDR-005, extend the existing records this change relies on, and verify `python3 scripts/check_tdr.py` passes (2026-11-10)
- [ ] 0.2 rashodkorala reviews the built result and confirms, amends, or rejects each of the four records; verify every verdict is recorded in its Review Notes

## 1. Contract spine

TDRs: CDR-008, CDR-002, CDR-003, CDR-006, IDR-005

- [ ] 1.1 Add `Manner`, `PatientSignal`, `TrustCueKind`, `PatientSignalEntry`, `TrustCue`, `TrustUpdate`, the new line purposes, the `signal` entry kind, `TurnResult.manner`, `TurnCaption.manner`, `visit.state.signals`, and `visit.state.trust` to `server/contracts.py` and `web/lib/contracts.ts`; add `patient.signal` to the review commands and `visit.ask_if_clear` to the controller commands; add `trust.update` to the controller-only events; verify contract tests and `npm run check:contracts` pass with new fixtures
- [ ] 1.2 Add the notice and label keys to `web/lib/i18n.ts` and the five language files, all `_reviewer: pending`; verify the TypeScript build and a unit test that every language has every key

## 2. Server

TDRs: MDD-005, CDR-008, IDR-005, ADR-002, ADR-003, ADR-004, ADR-006, ADR-007, ADR-010, CDR-001, CDR-003, CDR-006, IDR-003, EDR-002

- [ ] 2.1 Read `manner` in the translate call with the IDR-005 definitions, frame rule, and tone-check wording; set it on `TurnResult` and on the caption of a final physician turn only; verify graph tests with the fake model cover a physician turn with a manner label, a patient turn with `manner: null` in its caption, and a frame adverb passing the tone check
- [ ] 2.2 Add `MANNER_DELIVERY` and `delivery_for_turn` to `server/voice.py` and use it in the speak gate; verify a unit test covers every manner and every emotion
- [ ] 2.3 Replace `server/empathy.py` with `server/trust.py`: the nudge as today, the deterministic reassurance-landed rule, the culture cue for physician turns, and a `trust.update` per settled final turn, controller only, held on the visit and sent in `visit.state.trust`; verify channel tests cover landed true, false, and null, a cue on a sensitive topic and none on an everyday one, and no `trust.update` reaching screen or review live or in a snapshot
- [ ] 2.4 Handle `patient.signal`: role rules, consent and pause rules, the two second hold, the `signal` chain entry, `patient.signal` to every role, the interpreter line in the physician's language for `not_understood` and `slower`, `repeat` refused before any spoken translation, and a `trust.update` with an understanding cue; verify channel tests cover every rule and that `record.integrity` follows the append
- [ ] 2.5 Handle `visit.ask_if_clear`: controller only, refused before consent, while paused, and during a read-back; one interpreter line in two languages speakable only in the patient's language; verify channel and speak-gate tests
- [ ] 2.6 Accept companion turns in the patient's language, refuse them in the physician's language, produce no nudge for them; verify channel tests and that the fake model relays with the companion frame
- [ ] 2.7 Write the signal and closing-check interpreter lines in `kb/content/interpreter/{en,fr,pa,ta,si}.yaml`, all `reviewer: pending`; verify a test loads every language and formats the name
- [ ] 2.8 Give the Anthropic client a 25 second timeout and two retries for live calls, so a hung call ends the turn as `failed` instead of hanging the visit; verify a unit test of the client settings and a channel test that a failing model yields `turn.status` `failed` and nothing spoken
- [ ] 2.9 Regenerate fixtures, run `uv run ruff check . && uv run ruff format --check . && uv run pytest`; verify all pass

## 3. Web: design system

TDRs: ADR-012, ADR-001

- [ ] 3.1 Write the tokens and base styles in `web/app/globals.css`, the fonts in `web/app/layout.tsx` and `web/package.json`, and the system in `web/design/README.md`; verify the build passes and a contrast check of every text token on its background meets AA
- [ ] 3.2 Rewrite `screen.module.css` and `SharedScreen.tsx` to the tokens with the manner label beneath physician translations, the patient signal notice in both languages, the companion label, and the orb colours derived from the speaker tokens; verify screenshots at 1920 by 1080 and 1280 by 720 in light and dark and `node e2e/week2.mjs` passes
- [ ] 3.3 Rewrite the home page, `RecordBadge`, `RecordView` and their stylesheets to the tokens, listing signals in the record view's timeline; verify `node e2e/record-note.mjs` and `node e2e/tamper.mjs` pass

## 4. Web: patient device and controller

TDRs: MDD-005, CDR-008, IDR-005, ADR-012, CDR-003, CDR-004, CDR-005, CDR-006, IDR-001

- [ ] 4.1 Build `/patient` (`PatientScreen.tsx`): consent, the latest caption in the patient's language with the manner label, the five controls, refusal notices, and the existing review content beneath; `/review` redirects to `/patient`; verify `node e2e/patient-voice.mjs` shows each signal on `/screen` in both languages, on `/control`, and in the record, a refused double tap, and replay without a new turn
- [ ] 4.2 Add the trust view, the companion control, the closing check control, the manner on the turn log, and the signal list to the controller, restyled to the tokens; verify `node e2e/trust-view.mjs` shows landed true and false, a culture cue, a signal with its suggestion, a companion turn labelled on `/screen`, and no trust data on `/screen` or `/patient`
- [ ] 4.3 Replay "say that again" on the controller through the speech endpoint and the speaking signal, so `/screen` shows Speaking during the replay; verify in `node e2e/patient-voice.mjs`
- [ ] 4.4 Restyle `ReviewScreen`, `ExplainBackPanel`, and `NoteSummaryPanel` to the tokens; verify `node e2e/review.mjs`, `node e2e/explain-back.mjs`, `node e2e/summary.mjs`, and `node e2e/summary-refused.mjs` pass

## 5. Verification

TDRs: EDR-002

- [ ] 5.1 Run every end-to-end script in `web/e2e/` against a fresh fake-model stack and review screenshots of every screen at 1920, 1280, and 390 pixels; verify all pass and no screen overflows
- [ ] 5.2 Run `scripts/dev.sh` with the live model and speak one visit in Punjabi: a reassuring physician turn carries its label and a warm voice, a worried patient turn reaches the controller with its emotion and a landed mark on the next calm turn, a patient signal is spoken to the physician; record it in docs/voice-test.md
- [ ] 5.3 Native speakers review the new labels and lines in all five languages; verify every `_reviewer: pending` on new content is replaced by a name
- [ ] 5.4 Fill `implementation_refs` and `test_refs` in MDD-005, ADR-012, CDR-008, and IDR-005; verify `python3 scripts/check_tdr.py` passes

## Workflow follow-up

- After rashodkorala's review (0.2), amend the demo-night stage script for the patient device and the manner labels, then archive with `/opsx:archive` together with `demo-night-mvp`.
