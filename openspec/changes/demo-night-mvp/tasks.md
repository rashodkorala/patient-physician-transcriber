# Tasks

## 0. Human decision review gate

TDRs: ADR-004, ADR-005, ADR-006, ADR-007, CDR-001, CDR-002, EDR-002, IDR-001, IDR-002, IDR-003, TDM-001

- [x] 0.1 Project lead reviews ADR-004, ADR-005, ADR-006, and ADR-007 and sets each to accepted or rejected; verify `python3 scripts/check_tdr.py` shows no pending ADRs
- [x] 0.2 Project lead and front-end and back-end owners review CDR-001 and CDR-002; verify both are accepted or replaced (2026-10-22: the project lead reviewed and accepted both as sole reviewer)
- [x] 0.3 A second team member reviews EDR-002, IDR-001, IDR-002, and IDR-003; TDM-001 is acknowledged; verify the review queue in `scripts/check_tdr.py` is empty (2026-10-22: no second reviewer available, so the project lead reviewed and accepted all records)
- [ ] 0.4 Write the demo script (lines for both speakers, featured condition, dose) and verify both native speakers and a clinician sign it off in docs/demo-script.md (draft written 2026-10-22; sign-offs pending). Test scripts docs/test-script-tamil.md and docs/test-script-sinhala.md (drafted 2026-10-23) need the same sign-offs from the Tamil and Sinhala speakers and the clinician
- [x] 0.5 Decide TDM-002 (presenter mismatch control); if accepted, add the presenter-only `demo.inject_mismatch` command to CDR-001 as an additive amendment; verify `python3 scripts/check_tdr.py` passes (2026-10-22: accepted with clarifications by the project lead; CDR-001 amended)

## 1. Week 1 (22 to 29 Oct): live loop

TDRs: ADR-001, ADR-005, ADR-006, ADR-007, CDR-001, CDR-002, IDR-001, EDR-002

- [x] 1.1 Scaffold `server/` (FastAPI, pyproject) and `web/` (Next.js), with one start script; verify both start and `/screen` connects to the WebSocket (2026-10-24: `scripts/dev.sh --prod` with `TRANSLATOR=fake`; `node web/e2e/week1.mjs` confirms `/screen` and `/control` connect)
- [x] 1.2 Implement CDR-001 and CDR-002 types in `server/contracts.py` and `web/lib/contracts.ts`; verify contract tests pass (2026-10-24: `uv run pytest` 17 passed; `npm run check:contracts` passes and fails on a private field in a caption)
- [ ] 1.3 Implement speech token minting and `web/lib/speech.ts` recognise and speak; verify Punjabi, French, and English round trip on the laptop (code done 2026-10-24; laptop check pending: needs Azure key and microphone; log in docs/speech-test.md)
- [ ] 1.4 Run the Punjabi accuracy test with the speaker on the demo script; record word error notes in docs/speech-test.md and switch to Google if it fails (ADR-005)
- [ ] 1.5 Build push-to-talk on `/control` and a plain translate path; verify a spoken turn appears on `/screen` with original and translation (code done 2026-10-24; verified with a typed turn and the fake translator by `node web/e2e/week1.mjs`; spoken turn pending on the laptop)
- [ ] 1.6 Build `/screen` bilingual caption layout with Gurmukhi font; verify readability at 3 metres on the TV (layout done 2026-10-24; TV check pending)
- [ ] 1.7 Log per-turn latency; verify the median is under 3 seconds for the demo lines (logging and CSV export on `/control` done 2026-10-24; real median pending on the laptop with live speech and Claude)

## 2. Week 2 (30 Oct to 5 Nov): knowledge base and tone-aware turn graph

TDRs: ADR-002, ADR-003, ADR-004, ADR-006, IDR-002, CDR-002, EDR-002

- [ ] 2.1 Write knowledge base content for the demo script (glossary, tone guides, empathy bank, condition explainer) with the native speakers; verify each file has a reviewer noted (drafts in `server/kb/content/` and `web/i18n/` 2026-10-24, all marked `reviewer: pending`; Punjabi and French speaker review pending)
- [ ] 2.2 Build the Chroma index and retrieval with exact-match glossary lookup; verify retrieval tests for terms and emotions pass offline (built 2026-10-24; `tests/test_kb.py` passes offline with the hashing test embedder; the E5 model could not be downloaded in the build container, so the same tests are pending on the laptop after `uv run python scripts/download_model.py`)
- [x] 2.3 Implement the LangGraph turn graph (analyse, retrieve, translate, verify, retry, block, escalate) with status events; verify graph tests with a mocked model cover pass, retry, block, and escalate (CDR-002 status table) (2026-10-24: `tests/test_turn_graph.py` covers every CDR-002 row and the precedence order; server suite 52 passed)
- [x] 2.4 Add translation-register tone labels to spoken captions; verify each spoken caption shows one label and no shared or review screen ever receives emotion, certainty, or back-translation (CDR-001 routing test) (2026-10-24: `tests/test_visit_channel.py` routing tests; `node web/e2e/week2.mjs` checks one label per spoken caption and no private field in any `/screen` frame)
- [x] 2.5 Implement empathy nudges on `/control` only; verify `/screen` never receives `empathy.nudge`, including through a `visit.state` snapshot when the TV connects mid read-back (2026-10-24: server tests and `node web/e2e/week2.mjs`, which opens a second `/screen` during read-back)
- [ ] 2.6 Implement critical value read-back and blocking; verify a dose still mismatched after one retry is blocked, never spoken or shown on the shared screen, and the speaker is asked to repeat; a matched dose waits for physician confirmation; a matched dose with a failed tone check is escalated, not read back; in tests and live (built 2026-10-24; verified in server tests and in the browser by `node web/e2e/week2.mjs` with the fake model; live check with Claude and speech pending on the laptop)
- [ ] 2.7 Run the ten-line tone set with both speakers; record ratings in docs/tone-ratings.md and verify average respect and warmth of 4 or more (needs both speakers and the live model)

## 3. Week 3 (6 to 12 Nov): remaining demo beats

TDRs: ADR-003, ADR-006, IDR-003, CDR-001, CDR-002

- [ ] 3.1 Language picker with thirteen languages in their own scripts; verify only Punjabi and French are selectable
- [ ] 3.2 Consent screen in Punjabi and French; verify conversation is blocked until consent
- [ ] 3.3 Off-the-record pause, human interpreter button with connecting state, and "mark high risk" on the controller; verify all notices appear in both languages and a high-risk mark offers an interpreter
- [ ] 3.4 Explain-back chain and view; verify a missed frequency is flagged
- [ ] 3.5 Transcript review with re-speak corrections keeping originals; verify history shows both
- [ ] 3.6 Note with provenance tags and click-to-source; verify every sentence has a tag and a link
- [ ] 3.7 Patient summary in the patient's language, read aloud, with deterministic dose check; verify a mismatched dose is refused
- [ ] 3.8 Hash chain, record verified badge, and hidden tamper control; verify tests detect alteration and the badge turns red live

## 4. Week 4 (13 to 19 Nov): safety net and rehearsal

TDRs: TDM-001, EDR-002

- [ ] 4.1 Record a full rehearsal event log and build replay mode; verify replay runs with the network disconnected
- [ ] 4.2 Polish the TV layout and controller shortcuts; verify the full script runs without touching the mouse on `/screen`
- [ ] 4.3 Dress rehearsal 1 on 17 Nov with both speakers on the real TV and microphone; record issues in docs/rehearsals.md
- [ ] 4.4 Dress rehearsal 2 on 18 Nov; record the backup video; verify all nine beats pass for both languages
- [ ] 4.5 Fill `implementation_refs` and `test_refs` in every TDR used; verify `python3 scripts/check_tdr.py` passes

## 5. Demo safety beat (presenter mismatch control)

TDRs: TDM-002, ADR-004, CDR-001, CDR-002

- [ ] 5.1 Implement the presenter-only `demo.inject_mismatch` and `demo.cancel_injection` commands, the `demo.injection_state` event, and the one-shot injection in the turn graph; verify tests show the armed flag waits through a turn without critical values, multiplies the first dose number by 10 on the next one, that turn is blocked on both attempts, the following turn is unaffected, cancel works, and no screen or review connection receives injection state, live or via `visit.state`
- [ ] 5.2 Mark injections on the controller and in the record view only, show the injected turn on the review screen as blocked, then repeated, and add the simulated interpreter connection close; verify all three in a scripted run of docs/demo-script.md beats 5, 6, and 8

## 6. Sinhala and Tamil test runs (test mode only)

TDRs: TDM-003, ADR-002, ADR-005, ADR-006, IDR-002

- [ ] 6.1 Add test mode as a server start-up setting (off by default, restart to change, no runtime toggle) with a controller-only banner; verify Sinhala and Tamil are selectable only when started in test mode, the shared and review screens show no banner, and the stage checklist in docs/demo-script.md covers it
- [ ] 6.2 Check speech recognition and voices for Sinhala and Tamil (ADR-005; Google backup if Azure fails a language); verify a short round trip in each and record the result in docs/speech-test.md
- [ ] 6.3 Write knowledge base content for en-si and en-ta (glossary, tone and honorifics, empathy phrases, type 2 diabetes and high blood pressure explainers) with the native speakers; verify each file names its reviewer and retrieval tests pass offline
- [ ] 6.4 Run docs/test-script-tamil.md and docs/test-script-sinhala.md in full at least twice each, with each speaker's agreement and fictional content only; verify every test log row is filled in, no audio is retained, and test-run replay logs are deleted after the summary
- [ ] 6.5 Summarise both runs in docs/language-benchmark.md (latency, retries, blocks, escalations, tone ratings, verdict); verify the project lead has read it before the 17 November rehearsal

## Workflow follow-up

- After demo night, let TDM-001 expire, decide which demo TDRs carry into `add-multilingual-medical-consultation`, and archive this change with `/opsx:archive`.
