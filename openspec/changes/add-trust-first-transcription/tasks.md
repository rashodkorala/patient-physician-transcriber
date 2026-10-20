# Tasks

## 1. Foundation

- [ ] 1.1 Choose the stack per design decision 7, scaffold the repository (front end, backend, database migrations), and verify the app boots locally and CI runs an empty test suite
- [ ] 1.2 Define the core data model (patient, physician, visit, consent, segment, amendment, note sentence, audit entry) and verify migrations apply cleanly to an empty database
- [ ] 1.3 Add authentication with separate patient and physician roles and verify role-based access tests pass

## 2. Audit integrity

- [ ] 2.1 Implement the append-only, hash-chained audit log and verify tests show an intact chain passes and an altered or deleted entry is detected
- [ ] 2.2 Implement content fingerprints for finalised transcripts and notes plus a "verify my copy" endpoint, and verify a matching and a modified copy are reported correctly
- [ ] 2.3 Implement the patient-visible access log and verify every read, export, and processing step in tests produces an entry
- [ ] 2.4 Configure encryption at rest and in transit and verify stored blobs are unreadable without keys
- [ ] 2.5 Document the audit model and how to run an integrity check in docs/audit.md

## 3. Consent management

- [ ] 3.1 Build the consent screen with scope choice and retention notice, and verify consent cannot be given before the notice is shown
- [ ] 3.2 Gate the capture client on a valid consent record and verify recording cannot start without one
- [ ] 3.3 Implement the off-the-record pause on the client and verify in tests that no audio is transmitted during a pause and a marker appears in the transcript
- [ ] 3.4 Implement transcript-only audio deletion and consent revocation, and verify data is removed and audit entries are written

## 4. Speaker-attributed transcription

- [ ] 4.1 Benchmark at least two speech-to-text vendors with diarisation on sample consultation audio and record the choice in design.md
- [ ] 4.2 Implement stage 1 ingestion (audio to diarised segments with timings and confidence) and verify against a recorded fixture
- [ ] 4.3 Implement stage 2 role assignment (patient, physician, companion, unknown) with speaker confidence and verify on a fixture with a companion
- [ ] 4.4 Implement low-confidence flagging and the finalisation block, and verify a flagged segment prevents finalisation
- [ ] 4.5 Build the shared transcript view for patient and physician and verify both roles see the same labelled transcript

## 5. Patient verification

- [ ] 5.1 Implement patient confirm, correct, and add-context actions on their own segments, and verify amendments never overwrite the original
- [ ] 5.2 Implement speaker disputes and physician resolution, and verify sign-off is blocked while disputes are open
- [ ] 5.3 Implement physician sign-off with side-by-side disagreements, and verify all four verification statuses are reachable in tests
- [ ] 5.4 Implement the review window with reminders and the "not patient-reviewed" outcome, and verify with a time-travel test

## 6. Note provenance

- [ ] 6.1 Implement grounded note generation returning sentences with segment citations and provenance tags, and verify output schema validation
- [ ] 6.2 Implement the citation post-check that downgrades unsupported or mismatched sentences to AI inference, and verify with adversarial fixtures
- [ ] 6.3 Build the note view with click-to-source and audio playback, and verify links resolve to the right segments
- [ ] 6.4 Flag dependent note sentences when a segment is amended, and verify the flag appears for the physician
- [ ] 6.5 Enforce physician approval before export and verify unapproved export is refused

## 7. Patient summary

- [ ] 7.1 Generate the plain-language summary with language and reading-level options, and verify output for at least two languages
- [ ] 7.2 Implement question detection and the "questions answered" list, and verify an unanswered question is marked
- [ ] 7.3 Link summary statements to sources and gate release on physician approval, and verify a pending summary is hidden from the patient

## 8. Tone coaching

- [ ] 8.1 Implement physician opt-in and the private tone store, and verify another user is denied access
- [ ] 8.2 Implement interruption, jargon, unanswered-question, and speaking-time signals linked to segments, and verify on a fixture consultation
- [ ] 8.3 Build the post-visit tone summary view and verify tone data is absent from note and summary exports

## 9. Integration and pilot readiness

- [ ] 9.1 Run an end-to-end test from consent through capture, transcription, patient review, physician sign-off, note export, and summary release, and verify the audit chain is intact at the end
- [ ] 9.2 Run a scripted hallucination and omission audit on a sample of generated notes and record rates against the success metrics
- [ ] 9.3 Complete a privacy and compliance checklist (BAA or DPA with each vendor, retention settings, residency) for the pilot region

## Workflow follow-up

- Archive the change with `/opsx:archive` after review and pilot sign-off.
- Verify the archived specs under `openspec/specs/` contain all seven capabilities.
