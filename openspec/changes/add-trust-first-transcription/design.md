# Design

## Context

Greenfield project with no existing code. Motivation is in `proposal.md` (Why) and the market review in `docs/product-research.md`. Requirements live in the seven spec deltas under `specs/`. The stack is not yet chosen, so decisions below name the preferred option and the alternatives.

Constraints that shape the design:
- Protected health information throughout, so every processor needs a BAA (US) or DPA (UK, EU, Canada), and data residency must be configurable per deployment.
- The physician is the legal author of the record; the patient's role is verification and amendment, never direct editing of the note.
- Two very different users: a physician in a time-pressured clinic and a patient at home on a phone.

## Goals / Non-Goals

**Goals:**
- One verifiable data model where transcript segments are the single source of truth, and the note, patient summary, and tone feedback all reference segments by identifier.
- Tamper evidence that a patient or auditor can check without trusting the operator's database.
- A first version usable in a single clinic without EHR integration.

**Non-Goals:**
- Real-time, in-visit tone nudges (post-visit only in this change).
- EHR write-back (Epic, Oracle Health, and others); export is manual.
- Clinical decision support or billing code suggestion.
- Fully on-device transcription.

## Decisions

### 1. Segments as the unit of truth
Every artefact references transcript segments by stable identifier. Amendments are new records pointing to a segment; the original segment text is immutable.
- *Why:* makes provenance, patient verification, and amendment history fall out of one model.
- *Alternative considered:* storing the note as free text with offsets into the transcript. Rejected because offsets break on amendment.

### 2. Two-stage pipeline: speech-to-text with diarisation, then role assignment
Stage 1 uses a managed speech-to-text service that returns diarised speakers (anonymous speaker A, B, C) with word timings and confidence. Stage 2 maps anonymous speakers to roles (patient, physician, companion) using a short enrolment of the physician's voice plus an LLM pass over content, and produces a speaker confidence.
- *Why:* diarisation services do not know roles; separating the stages lets us swap vendors.
- *Options:* Deepgram, AssemblyAI, AWS Transcribe Medical, Azure Speech, or self-hosted Whisper with pyannote. Choose on BAA availability, diarisation accuracy on medical audio, and residency.

### 3. Grounded note generation with mandatory citations
The LLM receives the segment list with identifiers and must return each note sentence with the segment identifiers that support it and a provenance tag. A post-check verifies every cited segment exists and that a stated tag matches the cited segment's speaker; failures downgrade the sentence to AI inference.
- *Why:* enforces "inference is never quoted" mechanically rather than by prompt alone.
- *Alternative considered:* free-form generation followed by retrieval-based alignment. Rejected as less reliable for attribution.

### 4. Hash-chained audit log with external anchoring
Each audit entry stores the hash of the previous entry. Finalised transcripts and notes get a SHA-256 content fingerprint recorded in the chain. The chain head is periodically anchored to an external, append-only location (for example a write-once object store bucket or a public transparency log).
- *Why:* gives detectable tampering even against a privileged operator, and lets patients verify downloaded copies.
- *Alternative considered:* blockchain storage. Rejected for cost, latency, and the risk of putting health data near a public ledger; only hashes leave the system.

### 5. Consent as a gate in the capture client
The capture client cannot open the microphone without a valid consent record for the visit, and the off-the-record control stops the audio stream on the client so paused audio never leaves the device.
- *Why:* privacy by construction rather than by server-side filtering.

### 6. Tone analysis over the verified transcript
Tone signals (interruptions from overlapping timings, unexplained jargon from a medical term list checked against nearby lay explanation, unanswered questions from question detection plus answer linking) run after transcription, and results are stored in a separate, physician-scoped store.
- *Why:* keeps coaching data physically and logically separate from the medical record.

### 7. Application shape
A web application (responsive, works on a phone) for both patient portal and physician view, plus a lightweight capture client (browser first, native mobile later). Backend as a small set of services: capture ingest, transcription pipeline, note service, audit service.
- *Options:* TypeScript (Next.js) front end with a Python or TypeScript backend; Postgres for relational data; object storage for audio. Final choice deferred to the first apply session.

## Risks / Trade-offs

- [Diarisation errors on overlapping speech or similar voices] → low-confidence flagging forces review; patient and physician can reattribute.
- [LLM hallucination in notes] → mandatory citations, automatic downgrade to AI inference, physician approval before export.
- [Patients do not complete review] → review window with reminders; record "not patient-reviewed" honestly instead of blocking care.
- [Tone feedback perceived as surveillance by physicians] → strictly opt-in, private, excluded from the record, and never shared without explicit grant.
- [Off-the-record pauses reduce documentation completeness] → physician can add a manual note for the paused interval; the gap is visible.
- [Translation errors in patient summaries] → summaries are physician-approved and link back to source; offer original-language view.
- [Regulatory variation across regions] → residency and retention settings per deployment; legal review before each region launch.

## Migration Plan

Not applicable: greenfield. Rollout plan is a single-clinic pilot, then measurement against the success metrics in `docs/product-research.md` before wider release.

## Open Questions

- Which speech-to-text vendor gives the best diarisation on medical audio under a BAA in our first launch region? (Benchmark during apply; does not change the specs.)
- Default review window length (proposed: 7 days) and default confidence threshold (proposed: 0.85), to be tuned in the pilot.
- First launch region (affects residency settings, not the specs).
