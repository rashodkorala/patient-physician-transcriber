# Proposal

## Why

Demo night is on 19 November 2026. We need a live, convincing demonstration that a patient and a physician who do not share a language can understand each other, with warmth and respect carried across, and can both trust the record afterwards. The full roadmap (`add-multilingual-medical-consultation`) is too large for four weeks, so this change delivers a focused slice (MDD-003).

## What Changes

A nine-beat demo for Punjabi to English and French to English, run locally on one laptop with a TV:

1. **Language picker**: thirteen languages listed in their own scripts; Punjabi and French live, others marked "coming soon".
2. **Consent** in the patient's language, one tap.
3. **Live tone-aware interpretation**: push-to-talk per speaker; side-by-side captions on the TV with tone labels; translation spoken aloud using approved medical terms, respectful register, and preserved warmth; private empathy nudge for the physician when the patient sounds worried.
4. **Dose read-back**: numbers, doses, and frequencies highlighted and confirmed before the patient hears them.
5. **Explain-back**: the patient repeats the plan in their language; the physician sees what matched and what was missed.
6. **Off-the-record pause** and a **human interpreter** button (simulated connection; also offered automatically on low confidence).
7. **Transcript review**: speaker-labelled, bilingual; patient confirms or corrects by re-speaking; originals kept.
8. **Note and summary**: English note with each sentence tagged patient-stated, physician-stated, companion-stated, interpreter-stated, or AI inference (only the first two and AI inference occur, since the demo captures patient and physician turns only); Punjabi or French summary read aloud.
9. **Record verified** badge, with a tamper demonstration that turns it red.

Also: a replay mode that plays a recorded session through the same screens if the network fails, and a presenter-only mismatch control that forces one blocked dose on stage (TDM-002). The full stage script is `docs/demo-script.md`. Before demo night, Sinhala and Tamil are tested off stage in a test mode set when the server starts (TDM-003) using `docs/test-script-tamil.md` and `docs/test-script-sinhala.md`.

## Capabilities

### New Capabilities
- `demo-consultation-flow`: the end-to-end demo consultation experience across the nine beats and replay mode.

### Modified Capabilities
None.

## Decisions (TDRs)

- Accepted (all on 2026-10-22 by the project lead): MDD-001, MDD-002, MDD-003, ADR-001, ADR-002, ADR-003, ADR-004 (LangGraph), ADR-005 (speech provider), ADR-006 (models), ADR-007 (in-memory state), CDR-001 (visit events), CDR-002 (turn result), EDR-001, EDR-002 (testing), IDR-001 (push-to-talk), IDR-002 (retrieval), IDR-003 (hash chain), TDM-001 (replay mode), TDM-002 (presenter mismatch control, accepted with clarifications), TDM-003 (Sinhala and Tamil test languages, accepted with clarifications on 2026-10-24).
- Registry: `openspec/tdr/index.md`.

## Out of Scope

Login and accounts, any database, language quality tiers, data residency and vendor agreements, communication coaching, real human interpreter integration, live use of the other ten languages, automatic speaker diarisation, EHR export, and deployment beyond the demo laptop.

## Impact

- New `server/` (Python) and `web/` (Next.js) folders.
- External services: speech recognition and synthesis, and an LLM provider (keys held server-side).
- Knowledge base content written and checked by the team's Punjabi and French speakers.
