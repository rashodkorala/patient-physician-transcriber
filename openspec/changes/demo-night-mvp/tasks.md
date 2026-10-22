# Tasks

## 0. Human decision review gate

TDRs: ADR-004, ADR-005, ADR-006, ADR-007, CDR-001, CDR-002, EDR-002, IDR-001, IDR-002, IDR-003, TDM-001

- [x] 0.1 Project lead reviews ADR-004, ADR-005, ADR-006, and ADR-007 and sets each to accepted or rejected; verify `python3 scripts/check_tdr.py` shows no pending ADRs
- [x] 0.2 Project lead and front-end and back-end owners review CDR-001 and CDR-002; verify both are accepted or replaced (2026-10-22: the project lead reviewed and accepted both as sole reviewer)
- [x] 0.3 A second team member reviews EDR-002, IDR-001, IDR-002, and IDR-003; TDM-001 is acknowledged; verify the review queue in `scripts/check_tdr.py` is empty (2026-10-22: no second reviewer available, so the project lead reviewed and accepted all records)
- [ ] 0.4 Write the demo script (lines for both speakers, featured condition, dose) and verify both native speakers sign it off in docs/demo-script.md

## 1. Week 1 (22 to 29 Oct): live loop

TDRs: ADR-001, ADR-005, ADR-006, ADR-007, CDR-001, CDR-002, IDR-001, EDR-002

- [ ] 1.1 Scaffold `server/` (FastAPI, pyproject) and `web/` (Next.js), with one start script; verify both start and `/screen` connects to the WebSocket
- [ ] 1.2 Implement CDR-001 and CDR-002 types in `server/contracts.py` and `web/lib/contracts.ts`; verify contract tests pass
- [ ] 1.3 Implement speech token minting and `web/lib/speech.ts` recognise and speak; verify Punjabi, French, and English round trip on the laptop
- [ ] 1.4 Run the Punjabi accuracy test with the speaker on the demo script; record word error notes in docs/speech-test.md and switch to Google if it fails (ADR-005)
- [ ] 1.5 Build push-to-talk on `/control` and a plain translate path; verify a spoken turn appears on `/screen` with original and translation
- [ ] 1.6 Build `/screen` bilingual caption layout with Gurmukhi font; verify readability at 3 metres on the TV
- [ ] 1.7 Log per-turn latency; verify the median is under 3 seconds for the demo lines

## 2. Week 2 (30 Oct to 5 Nov): knowledge base and tone-aware turn graph

TDRs: ADR-002, ADR-003, ADR-004, ADR-006, IDR-002, CDR-002, EDR-002

- [ ] 2.1 Write knowledge base content for the demo script (glossary, tone guides, empathy bank, condition explainer) with the native speakers; verify each file has a reviewer noted
- [ ] 2.2 Build the Chroma index and retrieval with exact-match glossary lookup; verify retrieval tests for terms and emotions pass offline
- [ ] 2.3 Implement the LangGraph turn graph (analyse, retrieve, translate, verify, retry, block, escalate) with status events; verify graph tests with a mocked model cover pass, retry, block, and escalate (CDR-002 status table)
- [ ] 2.4 Add translation-register tone labels to spoken captions; verify each spoken caption shows one label and no shared or review screen ever receives emotion, certainty, or back-translation (CDR-001 routing test)
- [ ] 2.5 Implement empathy nudges on `/control` only; verify `/screen` never receives `empathy.nudge`
- [ ] 2.6 Implement critical value read-back and blocking; verify a dose still mismatched after one retry is blocked, never spoken or shown on the shared screen, and the speaker is asked to repeat; a matched dose waits for physician confirmation; a matched dose with a failed tone check is escalated, not read back; in tests and live
- [ ] 2.7 Run the ten-line tone set with both speakers; record ratings in docs/tone-ratings.md and verify average respect and warmth of 4 or more

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

## Workflow follow-up

- After demo night, let TDM-001 expire, decide which demo TDRs carry into `add-multilingual-medical-consultation`, and archive this change with `/opsx:archive`.
