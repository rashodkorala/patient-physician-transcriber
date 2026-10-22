# Design

## Context

> **Status: parked roadmap.** The current product is `demo-night-mvp`. Do not apply this change yet. It moves to product only if the demo works really well: after demo night (19 November 2026), a human decides whether to unpark it, and the demo's records may then be proposed again as product TDRs, with rehearsal and demo-night evidence. The only accepted records that bind this change are MDD-001, MDD-002, ADR-003, and EDR-001 (they list it in `related_changes`). ADR-003's escalation rules apply here, except its demo-only sentence that the interpreter call is simulated. All stack, vendor, state, and contract records remain scoped to `demo-night-mvp` and do **not** bind this change. The decisions below are design intent, not settled choices: before any task beyond group 0 starts, each technical choice must be recorded as a product TDR listing this change and accepted by a human (see task group 0).

Motivation is in `proposal.md` (Why) and `docs/product-research.md`. Requirements live in the eight spec deltas under `specs/`. Stack, vendor, and storage choices are deliberately left open (see Open Questions); the demo's choices may be proposed again as product TDRs, but they are not inherited.

Constraints that shape the design:
- Personal health information throughout: every processor needs a DPA (and a BAA for any US processing), and Canadian data residency must be available.
- Interpretation is live, so end-to-end latency per utterance must stay low enough for natural turn-taking (target under 3 seconds from end of speech to translated audio).
- Thirteen languages with very different machine translation quality; Sinhala, Tamil, Punjabi, Urdu, and Tagalog are expected to be weaker on medical content than Spanish, Portuguese, or Mandarin.
- The physician is the legal author of the record; the patient verifies and amends but never edits the note directly.
- Three surfaces: a large in-room screen everyone reads, a physician control device, and the patient's own phone for consent, review, and summary.

## Goals / Non-Goals

**Goals:**
- Safe live interpretation in a consulting room with bilingual captions on a shared screen.
- One data model where bilingual transcript segments are the single source of truth for the note, the patient summary, and coaching.
- Tamper evidence a patient or auditor can check without trusting the operator.
- A first version usable in a single clinic without EHR integration.

**Non-Goals:**
- Telehealth and remote interpretation between separate devices (later change).
- Sign languages (later change, needs video models and Deaf community input).
- EHR write-back; export is manual.
- Clinical decision support or billing codes.
- Fully on-device processing.

## Decisions

### 1. In-room setup: shared screen, room microphone, physician controller
A TV or monitor connected to a small client device (browser in kiosk mode on a mini PC, Chromecast-style stick, or smart TV browser) shows the live captions. A single conference microphone or two lapel microphones capture audio. The physician controls the session from a tablet or phone (start, pause, mark high risk, comprehension check, call interpreter). The patient also has a large pause and human-interpreter button on the shared screen's companion tablet.
- *Why:* one screen both people read builds shared trust in what is being said; no app install needed for the patient during the visit.
- *Alternative considered:* each person on their own phone. Deferred to the telehealth change because of pairing complexity.
- *Microphone choice:* two lapel microphones give each speaker a separate channel, making speaker attribution much more reliable; a single conference microphone is cheaper. Pilot both.

### 2. Turn-based (consecutive) interpretation
The system translates after each utterance ends, detected by voice activity and a short silence, with a manual "done speaking" control as fallback. Translation is spoken aloud in the listener's language and shown on screen.
- *Why:* consecutive interpretation is the norm for medical interpreters, gives complete sentences to translate (higher accuracy), and allows read-back of critical values before the listener hears them.
- *Alternative considered:* simultaneous streaming translation. Rejected for the first version because partial sentences translate badly and critical values cannot be confirmed.

### 3. Pipeline: speech recognition, translation, synthesis, with checks between
1. Speech recognition with language identification and diarisation produces the original-language segment with confidence.
2. Critical value extraction (numbers, doses, units, frequencies, dates, medications) runs on the original.
3. Translation uses an LLM constrained by the medical glossary for the language pair, returning the translation plus a back-translation.
4. Confidence combines recognition confidence, a back-translation similarity score, and critical value agreement between original and translation.
5. Text-to-speech speaks the translation only when checks pass and, for any physician turn with critical values, after the physician confirms them. Outcome order, as in the demo: blocked (critical value still mismatched after one re-translation), then escalated (confidence or tone still failing), then read-back, then final. A passing automated check never skips physician confirmation of a dose, and unspoken translations are never shown on shared screens.
- *Vendors:* not decided here. Speech recognition, translation, and speech synthesis vendors per language are a product TDR drafted from the benchmark in task group 2 and accepted before task group 5 (see Open Questions).
- *Why:* separating stages lets us choose the best vendor per language and insert safety checks.

### 4. Language quality tiers from our own benchmark
Before launch, a bilingual clinician panel scores translations of a fixed set of consultation scripts per language. Each language is assigned a tier that sets its confidence threshold and how readily a human interpreter is offered. Tiers are configuration, re-measured when vendors or models change.
- *Why:* published studies show large quality gaps between languages; assuming tiers is unsafe.

### 5. Human interpreter integration
Escalation launches a call to a contracted remote interpreting service (for example a Canadian provider with phone and video interpreters in all thirteen languages) and pipes the interpreter's audio into the room and the transcript as speaker role interpreter.
- *Why:* the product makes AI the default and humans one tap away, rather than replacing interpreters.
- *Alternative considered:* no integration (tell staff to call). Rejected because the hand-off must be recorded and fast.

### 6. Bilingual segments as the unit of truth
Every artefact references transcript segments by stable identifier. Each segment stores language, original text, translation, back-translation, and all confidences. Amendments are new records pointing to a segment; originals are immutable.
- *Why:* provenance, verification in either language, and amendment history fall out of one model.

### 7. Grounded note and summary generation
The LLM receives bilingual segments with identifiers and must return each note sentence with cited segment identifiers and a provenance tag. A post-check confirms citations exist and tags match speakers; failures downgrade to AI inference. Patient summaries reuse the same mechanism, and a deterministic check compares every critical value in the summary to the verified record.

### 8. Hash-chained audit log with external anchoring
Each audit entry stores the hash of the previous entry and the fingerprint of any content it refers to, never the content itself; finalised transcripts, notes, and summaries get a SHA-256 content fingerprint. Content lives in separate storage, so revocation deletes the content and appends a tombstone entry with its fingerprint: the chain stays valid and a downloaded copy can still be checked. The chain head is periodically anchored to a write-once store outside the main database. Retaining fingerprints of deleted content needs privacy review before launch.

### 8a. Capabilities by consent scope (normative for consent-management)

| Capability | Full | Transcript only | Interpret only | No AI |
|---|---|---|---|---|
| medical-interpretation | Yes | Yes | Yes (live only) | Human interpreter only |
| speaker-attributed-transcription | Yes | Yes | During the visit only; discarded at end | No |
| patient-verification | Yes | Yes | No | No |
| note-provenance | Yes, with audio playback | Yes, text links only | No AI note | No AI note |
| audit-integrity | Yes, incl. verify-my-copy | Yes, incl. verify-my-copy | Consent, interpreter hand-off, and access events; no content; no verify-my-copy | Consent, interpreter hand-off, and access events; no content; no verify-my-copy |
| communication-coaching | Yes (if opted in) | Yes (if opted in) | No | No |
| patient-summary | Yes | Yes | No | No |

Revocation of any scope deletes content not legally required and leaves fingerprint tombstones in the audit chain.
- *Alternative considered:* a blockchain. Rejected for cost, latency, and risk; only hashes leave the system.

### 9. Application shape
Surfaces: the shared screen (kiosk), physician controller, and patient portal. Backend responsibilities: live sessions, the interpretation pipeline, note and summary generation, and audit, with all data in a Canadian region.
- *Not decided here:* languages and frameworks, the live session channel, relational and audio storage, and pipeline orchestration are product TDRs accepted in task group 0 (see Open Questions).

## Risks / Trade-offs

- [Translation error in a dose or instruction causes harm] → critical value read-back, comprehension check, deterministic value matching in summaries, and human escalation for high-risk moments.
- [Low-resource languages (likely Sinhala) are not safe enough] → stricter tier thresholds, human interpreter offered at the start of every such visit, and the option to launch a language as human-first.
- [Latency makes conversation awkward] → consecutive mode, streaming recognition, and pre-warmed TTS voices; measure in the pilot.
- [Shared screen shows sensitive content to others in the room] → captions clear when the session ends, a privacy mode hides history, and the patient can pause at any time.
- [Dialect and code-switching (for example Punjabi and English mixed)] → language identification per segment, flagging of unexpected languages, and dialect options where vendors support them.
- [Diarisation errors in a three-person room] → lapel microphones per speaker where possible, low-confidence flagging, and reattribution.
- [Interpreter service cost or wait times] → escalate only on rules, record wait time as a metric, and negotiate per-minute pricing.
- [Coaching perceived as surveillance] → opt-in, private, excluded from the record.
- [Regulatory and French-language service obligations vary by province] → per-deployment residency and retention settings; legal review before each province launch.

## Migration Plan

Not applicable: greenfield. Rollout is a single-clinic pilot in a high-diversity Canadian city, then measurement against the success metrics in `docs/product-research.md` before wider release.

## Open Questions

**Decisions required as product TDRs before apply** (none of the demo's records carry over automatically):
- Architecture: languages and frameworks for front end and backend (group 0).
- Live session channel between screens and server (group 0).
- Storage: relational data and audio, in a Canadian region (group 0).
- Translation pipeline orchestration, LLM provider and models, and knowledge base retrieval (group 0).
- Speech recognition, translation, and synthesis vendors per language, from the benchmark (drafted in group 2, accepted before group 5).
- Contracts for every boundary between screens and server (CDRs, group 0).

- Automatic detection of high-risk moments (consent, serious diagnosis, end-of-life, crisis, safeguarding): drafted as ADR-008 (proposed); detection may only suggest a mark to the physician, never escalate or label on its own.

**Other open questions:**
- Default review window (proposed: 7 days) and starting confidence thresholds per tier, tuned in the pilot.
- Pilot province and clinic (affects residency and French-language settings, not the specs).
- Which remote interpreting provider to contract for escalation.
