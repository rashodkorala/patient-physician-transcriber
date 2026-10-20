# Proposal

## Why

Ambient AI scribes (Abridge, Dragon Copilot, Suki, Nabla, and others) save physicians time, but they are built for the clinician alone: patients rarely see the transcript, speaker mix-ups go unnoticed, published studies report hallucinations and omissions in a meaningful share of notes, and consent is a single verbal question. Patients who cannot see or verify what was recorded are less likely to disclose sensitive issues, which harms care. See `docs/product-research.md`.

We will build a trust-first transcription product, benchmarked against Abridge, in which the patient is a verifier of the record and every statement is traceable end to end.

## What Changes

- Introduce granular, per-visit, revocable consent with an "off the record" pause and a plain retention notice.
- Produce a speaker-attributed transcript (patient, physician, companion) with per-segment confidence, visible to both parties.
- Let the patient confirm or correct their own statements and the physician sign off on theirs; store corrections as amendments that preserve the original.
- Link every clinical note sentence to its transcript span and audio, tagged as patient-stated, physician-stated, or AI inference.
- Record every transcript, amendment, sign-off, and access in a tamper-evident, append-only audit trail that the patient can inspect.
- Give the physician a private, opt-in, post-visit tone summary (interruptions, unexplained jargon, unanswered questions).
- Give the patient a plain-language visit summary at a chosen reading level and language, including a list of their questions and the answers given.

## Capabilities

### New Capabilities
- `consent-management`: capturing, scoping, pausing, and revoking patient consent for recording and AI processing, and stating retention.
- `speaker-attributed-transcription`: turning consultation audio into a transcript where each segment carries a speaker role and confidence.
- `patient-verification`: patient confirmation and correction of their statements, physician sign-off, and amendment handling.
- `note-provenance`: tracing each clinical note sentence to its source segment and speaker, or marking it as AI inference.
- `audit-integrity`: tamper-evident storage of records and changes, and a patient-visible access log.
- `tone-coaching`: private, physician-only feedback on communication during a visit.
- `patient-summary`: plain-language, personalised visit summary for the patient.

### Modified Capabilities
None. This is the first change in the project.

## Impact

- New greenfield system: capture client (web or mobile), transcription and diarisation pipeline, note generation service, patient portal, physician review view, and audit store.
- External dependencies: a speech-to-text provider with speaker diarisation and an LLM provider, both under a BAA or DPA.
- Regulatory scope: HIPAA, PHIPA and PIPEDA, GDPR and UK GDPR. Patient right-to-amend and right-of-access processes are directly affected.
- EHR integration (Epic, Oracle Health, and others) is out of scope for this change; notes are exported manually in the first version.
