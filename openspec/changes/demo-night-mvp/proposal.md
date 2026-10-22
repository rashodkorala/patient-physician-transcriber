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
8. **Note and summary**: English note with each sentence tagged patient-said, physician-said, or AI inference; Punjabi or French summary read aloud.
9. **Record verified** badge, with a tamper demonstration that turns it red.

Also: a replay mode that plays a recorded session through the same screens if the network fails.

## Capabilities

### New Capabilities
- `demo-consultation-flow`: the end-to-end demo consultation experience across the nine beats and replay mode.

### Modified Capabilities
None.

## Decisions (TDRs)

- Accepted: MDD-001, MDD-002, MDD-003, ADR-001, ADR-002, ADR-003, EDR-001.
- Proposed, awaiting human review before the tasks that depend on them: ADR-004 (LangGraph), ADR-005 (speech provider), ADR-006 (models), ADR-007 (in-memory state), CDR-001 (visit events), CDR-002 (turn result), EDR-002 (testing), IDR-001 (push-to-talk), IDR-002 (retrieval), IDR-003 (hash chain), TDM-001 (replay mode).
- Registry: `openspec/tdr/index.md`.

## Out of Scope

Login and accounts, any database, language quality tiers, data residency and vendor agreements, communication coaching, real human interpreter integration, live use of the other ten languages, automatic speaker diarisation, EHR export, and deployment beyond the demo laptop.

## Impact

- New `server/` (Python) and `web/` (Next.js) folders.
- External services: speech recognition and synthesis, and an LLM provider (keys held server-side).
- Knowledge base content written and checked by the team's Punjabi and French speakers.
