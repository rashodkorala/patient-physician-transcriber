# Proposal

> **Status: parked roadmap.** The current product is `demo-night-mvp`. This change is not bound by the demo's decision records and must not be applied until its own product TDRs are accepted (tasks group 0). It moves to product only if the demo works really well: after demo night (19 November 2026), a human decides whether to unpark it, and the demo's records may then be proposed again as product TDRs, with rehearsal and demo-night evidence.

## Why

In Canada, most recent immigrants have a mother tongue other than English or French, and few physicians speak the most common non-official languages. Patients often rely on family members, frequently children, to interpret, which leads to misunderstanding, less disclosure, and worse care. AI interpreters exist but leave no verified record, and AI scribes produce a record but do not interpret. See `docs/product-research.md`.

We will build an AI medical interpreter that shows the conversation live in both languages on a shared in-room screen and produces a bilingual record that the patient verifies in their own language, with hand-off to a human interpreter whenever AI translation is not safe enough.

## What Changes

- Live, two-way medical interpretation between the patient's language and the physician's language, shown as side-by-side captions on a large shared screen and spoken aloud.
- Medical safeguards in interpretation: clinical glossary, read-back of numbers, doses, and dates, a comprehension check where the patient explains the plan back, and escalation to a qualified human interpreter on low confidence or high-risk moments.
- Per-language quality tiers that set confidence thresholds and escalation rules for each supported language.
- Consent, retention notice, and off-the-record pause presented in the patient's language.
- A speaker-attributed transcript in which every segment keeps the original speech, its translation, and translation confidence.
- Patient verification of their own statements in their own language, physician sign-off, and amendments that preserve originals.
- Clinical note sentences linked to original-language speech and its translation, tagged as patient-stated, physician-stated, or AI inference.
- Tamper-evident audit trail and patient-visible access log.
- Private, opt-in feedback to the physician on what was lost or misunderstood in translation.
- A plain-language visit summary in the patient's language with a "questions answered" list.
- First-version languages: English, French, Mandarin, Cantonese, Punjabi, Urdu, Arabic, Farsi, Tagalog, Spanish, Portuguese, Sinhala, and Tamil.

## Capabilities

### New Capabilities
- `medical-interpretation`: live, two-way speech interpretation between patient and physician on a shared screen, with medical safeguards, quality tiers, and human interpreter escalation.
- `consent-management`: capturing, scoping, pausing, and revoking patient consent in the patient's language, and stating retention.
- `speaker-attributed-transcription`: a bilingual transcript in which each segment carries speaker role, original language text, translation, and confidence.
- `patient-verification`: patient confirmation and correction of their statements in their own language, physician sign-off, and amendment handling.
- `note-provenance`: tracing each clinical note sentence to its source segment, speaker, and language, or marking it as AI inference.
- `audit-integrity`: tamper-evident storage of records and changes, and a patient-visible access log.
- `communication-coaching`: private, physician-only feedback on communication across the language barrier.
- `patient-summary`: plain-language, personalised visit summary in the patient's language.

### Modified Capabilities
None. This is the first change in the project.

## Impact

- New greenfield system: in-room display client (TV or monitor), microphone capture, physician control device, interpretation pipeline (speech recognition, translation, speech synthesis), note generation, patient portal, and audit store.
- External dependencies: speech recognition with language identification and diarisation, machine translation or LLM translation, text-to-speech for all first-version languages, and a human interpreter service (phone or video) for escalation. All must sign a DPA or BAA and support Canadian data residency.
- Regulatory scope: PIPEDA, PHIPA, Quebec Law 25, and other provincial health privacy acts; French-language service obligations where they apply.
- Human interpreter integration is limited to launching a call and recording that it happened; EHR integration is out of scope for this change.
