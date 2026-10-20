# Tasks

## 1. Foundation

- [ ] 1.1 Choose the stack per design decision 9, scaffold the repository (shared screen, physician controller, patient portal, backend, database migrations), and verify the app boots locally and CI runs an empty test suite
- [ ] 1.2 Define the core data model (patient, physician, visit, consent, bilingual segment, amendment, note sentence, summary, audit entry, interpreter hand-off) and verify migrations apply cleanly to an empty database
- [ ] 1.3 Add authentication with patient and physician roles and verify role-based access tests pass
- [ ] 1.4 Add internationalisation for all thirteen languages including right-to-left rendering, and verify UI snapshots for English, Arabic, Punjabi, and Sinhala

## 2. Language benchmark and tiers

- [ ] 2.1 Write a fixed set of consultation scripts covering history, examination, diagnosis, medications, and consent, and verify clinical review sign-off
- [ ] 2.2 Benchmark at least two speech recognition, translation, and speech synthesis options per language with a bilingual clinician panel, and record scores in docs/language-benchmark.md
- [ ] 2.3 Assign a quality tier and confidence threshold to each language from the benchmark, store them as configuration, and verify each language loads its tier
- [ ] 2.4 Build the medical glossary for each language pair from the benchmark scripts and verify glossary terms are used in translation tests

## 3. Audit integrity

- [ ] 3.1 Implement the append-only, hash-chained audit log and verify tests show an intact chain passes and an altered or deleted entry is detected
- [ ] 3.2 Implement content fingerprints and the "verify my copy" endpoint, and verify matching and modified copies are reported correctly
- [ ] 3.3 Implement the patient-visible access log in the patient's language and verify every read, export, interpreter hand-off, and processing step produces an entry
- [ ] 3.4 Configure encryption and Canadian data residency and verify stored blobs are unreadable without keys and reside in the configured region
- [ ] 3.5 Document the audit model and integrity check in docs/audit.md

## 4. Consent management

- [ ] 4.1 Build the language picker and consent screen with scope options and retention notice in all thirteen languages, with read-aloud, and verify consent cannot be given before the notice is shown
- [ ] 4.2 Gate capture on a valid consent record and verify capture cannot start without one
- [ ] 4.3 Implement the off-the-record pause with the bilingual paused notice on the shared screen, and verify no audio is transmitted during a pause
- [ ] 4.4 Implement the four consent scopes, including interpret-only with no retention, and revocation, and verify data is removed and audit entries are written

## 5. Live medical interpretation

- [ ] 5.1 Build the shared screen view with side-by-side bilingual captions, speaker labels, and correct script and direction, and verify readability at 3 metres on a 40-inch display
- [ ] 5.2 Build the physician controller (start, pause, mark high risk, comprehension check, call interpreter) and verify each control updates the shared screen
- [ ] 5.3 Implement the consecutive pipeline (recognition, translation with back-translation, synthesis) and verify end-to-end latency under 3 seconds on benchmark utterances
- [ ] 5.4 Implement critical value extraction and read-back confirmation, and verify a mistranslated dose is caught in tests
- [ ] 5.5 Implement the comprehension check with mismatch detection and verify an omitted dose in the patient's explanation is flagged
- [ ] 5.6 Implement low-confidence and high-risk escalation rules per tier and verify each triggers the human interpreter offer
- [ ] 5.7 Integrate the remote interpreter service, label interpreter segments, and record hand-offs, and verify with a sandbox call
- [ ] 5.8 Implement the "companion is interpreting" marker and verify it is recorded and interpretation is offered

## 6. Bilingual transcription

- [ ] 6.1 Implement per-segment language identification, diarisation, and role assignment (patient, physician, companion, interpreter, unknown), and verify on a three-person fixture
- [ ] 6.2 Store original text, translation, back-translation, and all confidences per segment, and verify an unexpected language is flagged
- [ ] 6.3 Implement low-confidence flagging with tier thresholds and the finalisation block, and verify a flagged segment prevents finalisation
- [ ] 6.4 Build the transcript view with each viewer's language first and verify patient and physician see the same segments

## 7. Patient verification

- [ ] 7.1 Build patient review in the patient's language with back-translation, confirm, correct, and add-context actions, and verify amendments never overwrite originals
- [ ] 7.2 Build physician review of translations with back-translation and amendment, and verify a corrected translation is sent to the patient
- [ ] 7.3 Implement speaker disputes, physician sign-off, side-by-side disagreements, and the four verification statuses, and verify each status is reachable in tests
- [ ] 7.4 Implement the review window with reminders in the patient's language and verify the "not patient-reviewed" outcome with a time-travel test

## 8. Note provenance

- [ ] 8.1 Implement grounded note generation in English or French with citations and provenance tags, and verify output schema validation
- [ ] 8.2 Implement the citation post-check and translation-unverified marking, and verify with adversarial fixtures
- [ ] 8.3 Build the note view with click-to-source showing original and translation, and verify links resolve correctly
- [ ] 8.4 Flag dependent note sentences on amendment and enforce physician approval before export, and verify both in tests

## 9. Patient summary

- [ ] 9.1 Generate the summary in the patient's language with reading level, language switch, and read-aloud, and verify output for Mandarin, Punjabi, and Arabic
- [ ] 9.2 Implement deterministic critical value matching and verify a summary with a mismatched dose is refused
- [ ] 9.3 Implement the "questions answered" list, source links, and physician approval with back-translation, and verify a pending summary is hidden from the patient

## 10. Communication coaching

- [ ] 10.1 Implement physician opt-in and the private feedback store, and verify another user is denied access
- [ ] 10.2 Implement poor-translation, lost-tone, misunderstanding, and speaking-balance signals linked to segments, and verify on a fixture consultation
- [ ] 10.3 Build the feedback view and verify feedback is absent from note and summary exports

## 11. Integration and pilot readiness

- [ ] 11.1 Run an end-to-end test from language choice and consent through live interpretation, escalation, transcript, patient review, sign-off, note export, and summary release, and verify the audit chain is intact
- [ ] 11.2 Run a per-language translation and hallucination audit on pilot-like sessions and record rates against the success metrics
- [ ] 11.3 Complete a privacy and compliance checklist (DPA with each vendor, residency, retention, French-language obligations) for the pilot province
- [ ] 11.4 Run usability sessions with patients in at least four languages and record findings in docs/usability.md

## Workflow follow-up

- Archive the change with `/opsx:archive` after review and pilot sign-off.
- Verify the archived specs under `openspec/specs/` contain all eight capabilities.
