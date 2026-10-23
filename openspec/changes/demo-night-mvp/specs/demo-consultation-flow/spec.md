# Spec Delta

## Purpose

Demonstrates, live on demo night, a consultation between a patient and a physician who do not share a language: tone-aware interpretation on a shared screen, safety checks, and a record both parties can verify.

## ADDED Requirements

### Requirement: Language selection
The system SHALL list the thirteen roadmap languages in their own scripts and SHALL allow Punjabi and French as live patient languages with English as the physician language, marking the others as coming soon. Only when the presenter enables test mode SHALL Sinhala and Tamil also be selectable; test mode is never used on stage.

#### Scenario: Choosing Punjabi
- **WHEN** the physician selects Punjabi as the patient language
- **THEN** the visit is set to interpret between Punjabi and English

#### Scenario: Unavailable language
- **WHEN** a user selects a language marked coming soon
- **THEN** the system explains it is not available in this demo and keeps the current selection

#### Scenario: Test languages hidden on stage
- **WHEN** test mode is off and a user selects Tamil or Sinhala
- **THEN** the language shows as coming soon and cannot be selected

#### Scenario: Test mode run
- **WHEN** the presenter enables test mode and selects Sinhala
- **THEN** the visit interprets between Sinhala and English with all the same checks as Punjabi and French

### Requirement: Consent in the patient's language
The system SHALL show a short consent notice in the patient's language and SHALL NOT start the conversation until the patient taps to consent.

#### Scenario: Consent given
- **WHEN** the patient taps consent on the Punjabi notice
- **THEN** the conversation screen becomes available and the consent time is recorded

### Requirement: Push-to-talk turns
The system SHALL capture each utterance through a speaker-specific control, so every turn records its speaker and language.

#### Scenario: Patient turn
- **WHEN** the physician presses the patient control and the patient speaks Punjabi
- **THEN** the turn is recorded with speaker patient and language Punjabi

### Requirement: Bilingual captions on the shared screen
The system SHALL show each spoken turn on the shared screen with the speaker label, the original text, and the translation side by side, readable from across the room. A translation SHALL appear on the shared screen only once it is spoken.

#### Scenario: Caption appears
- **WHEN** a turn without critical values passes its checks
- **THEN** the shared screen shows speaker, original, and translation together as it is spoken, within 3 seconds of the end of speech in normal conditions

#### Scenario: Dose awaiting confirmation
- **WHEN** a physician turn is waiting for read-back confirmation
- **THEN** the shared screen shows the original and a "checking the dose" notice in both languages, but not the translation

### Requirement: Translation is spoken aloud
The system SHALL speak each final translation aloud in the listener's language.

#### Scenario: Physician speaks to a Punjabi patient
- **WHEN** a physician turn in English is final
- **THEN** the Punjabi translation is spoken aloud

### Requirement: Tone-preserving translation
The system SHALL translate using approved medical terms and a respectful register for the listener's language, and SHALL keep the speaker's level of certainty and warmth.

#### Scenario: Reassurance
- **WHEN** the physician says a finding is very unlikely to be serious
- **THEN** the translation conveys the same low level of concern and a reassuring tone, and its back-translation does not express greater uncertainty

#### Scenario: Medical term
- **WHEN** the physician uses a medical term that has an approved translation
- **THEN** the translation uses the approved term and the shared screen shows a plain-language explanation beside it

### Requirement: Tone labels
The system SHALL show on each spoken caption one label describing the register of the translation: respectful, reassuring, empathetic, or neutral. Labels SHALL describe the translation, never the speaker's emotion.

#### Scenario: Label shown
- **WHEN** a spoken caption appears on the shared screen
- **THEN** it carries one translation-register label

### Requirement: Patient emotion stays with the physician
The system SHALL send detected emotion, certainty, and back-translations only to the physician's controller, never to the shared screen or review screens.

#### Scenario: Embarrassed patient
- **WHEN** a patient turn is analysed as embarrassed
- **THEN** the physician's controller may show it, and no shared or review screen receives that analysis

### Requirement: Empathy nudge
The system SHALL show the physician, and only the physician, a suggestion with a ready phrase when a patient turn expresses worry, embarrassment, pain, or confusion.

#### Scenario: Worried patient
- **WHEN** the patient says they are scared about the cost of medication
- **THEN** the physician's controller shows a nudge to acknowledge the worry with a suggested phrase, and the shared screen does not show it

### Requirement: Critical value read-back
The system SHALL detect numbers, doses, units, frequencies, dates, and medication names in a physician turn, highlight them in both languages, and require the physician to confirm them before the translation is spoken. Read-back SHALL only be offered when every critical value in the translation matches the original.

#### Scenario: Dose confirmed
- **WHEN** the physician says "take 500 milligrams twice a day", every value matches, and the physician confirms the highlighted values
- **THEN** the translation is spoken and the values appear highlighted on the shared screen

#### Scenario: Physician rejects read-back
- **WHEN** the physician rejects the highlighted values because the original was misheard
- **THEN** the turn is discarded without being spoken and the physician is asked to repeat

### Requirement: Critical value mismatch blocks speech
The system SHALL, on any turn, re-translate once when a critical value in the translation does not match the original, and SHALL block the turn if a value still does not match. A blocked turn SHALL never be spoken and SHALL NOT trigger automatic interpreter escalation.

#### Scenario: Mismatch corrected on retry
- **WHEN** the first translation changes "500 milligrams" and the re-translation matches it
- **THEN** the turn continues normally, with read-back for a physician turn

#### Scenario: Mismatch blocked
- **WHEN** a critical value still does not match the original after one automatic re-translation
- **THEN** the translation is not spoken, the controller shows the mismatched values in both languages, the speaker is asked to repeat or rephrase, and the shared screen shows only the original and a repeat notice, never the mismatched translation

### Requirement: Turn outcome precedence
The system SHALL give each turn exactly one outcome, choosing in this order: blocked, then escalated, then read-back, then final. A turn whose critical values match but whose confidence or tone check still fails SHALL be escalated, never read back or spoken.

#### Scenario: Matched dose with failed tone check
- **WHEN** a dose matches after verification but the tone check fails on both attempts
- **THEN** the turn is escalated, the dose is not offered for read-back, and nothing is spoken

### Requirement: Explain-back check
The system SHALL let the physician ask the patient to explain the plan back, and SHALL show which instructions were matched, missed, or contradicted.

#### Scenario: Missed instruction
- **WHEN** the patient's explanation omits the dose frequency
- **THEN** the physician sees the frequency marked as missed

### Requirement: Off-the-record pause
The system SHALL let either party pause capture, SHALL show a paused notice in both languages, and SHALL record nothing while paused.

#### Scenario: Pause
- **WHEN** the patient presses pause
- **THEN** the shared screen shows the paused notice in Punjabi and English and no turns are captured until resumed

### Requirement: Human interpreter offer
The system SHALL offer a human interpreter when a turn still fails its confidence or tone check after one retry or when the physician marks a moment as high risk, and SHALL let either party request one at any time, showing a connecting state in both languages. Critical value mismatches are blocked instead (see Critical value mismatch blocks speech).

#### Scenario: Low confidence
- **WHEN** a translation fails its confidence or tone check on the first attempt and again on the retry
- **THEN** the turn is marked uncertain, not spoken, its translation is not shown on the shared screen, and a human interpreter is offered in both languages

#### Scenario: Physician marks high risk
- **WHEN** the physician presses "mark high risk" before explaining a procedure that needs consent
- **THEN** a human interpreter is offered in both languages and the mark is recorded in the transcript

#### Scenario: Requested
- **WHEN** the patient presses the human interpreter button
- **THEN** a connecting state is shown and the request is recorded in the transcript

#### Scenario: Simulated connection ends
- **WHEN** a simulated interpreter connection has shown its connecting state for a few seconds
- **THEN** it closes with "Interpreter would join here (simulated)" in both languages and the consultation continues

### Requirement: Presenter mismatch control
The system SHALL provide a presenter-only control that, on the next physician turn containing a critical value, multiplies its first dose number by 10 in the translation on both attempts, so the normal mismatch rule blocks it. The presenter SHALL be able to cancel it before it fires. The injection SHALL be shown only on the controller and in the record view, never on the shared or review screens.

#### Scenario: Injected mismatch is blocked
- **WHEN** the presenter arms the control and the physician then says "0.4 milligrams"
- **THEN** the translation would read 4 milligrams, the turn is blocked, nothing is spoken, the speaker is asked to repeat, and the repeated turn proceeds to read-back normally

#### Scenario: Waits for a critical value
- **WHEN** the control is armed and the next physician turn contains no critical value
- **THEN** that turn is unaffected and the control stays armed

#### Scenario: Cancelled before firing
- **WHEN** the presenter cancels an armed control
- **THEN** the next dose is translated normally

#### Scenario: Review screen after an injection
- **WHEN** the patient opens the review screen after an injected turn
- **THEN** the turn appears as blocked, then repeated, with no wrong translation and no injection label

### Requirement: Transcript review
The system SHALL show the bilingual, speaker-labelled transcript after the visit, and SHALL let the patient confirm or correct their own turns while keeping the original text.

#### Scenario: Patient corrects a turn
- **WHEN** the patient re-speaks a correction for one of their turns
- **THEN** the turn shows the correction and its translation, and the original remains visible in its history

### Requirement: Note with provenance tags
The system SHALL generate an English clinical note in which every sentence carries exactly one provenance tag (patient-stated, physician-stated, companion-stated, interpreter-stated, or AI inference) and links to its source turns.

#### Scenario: Following a source
- **WHEN** the physician selects a note sentence tagged patient-stated
- **THEN** the source turn is highlighted with its original Punjabi and its translation

### Requirement: Patient summary
The system SHALL generate a plain-language summary in the patient's language, read it aloud on request, and keep every dose and number identical to the transcript.

#### Scenario: Summary read aloud
- **WHEN** the patient selects listen on the Punjabi summary
- **THEN** the summary is spoken in Punjabi and its dose matches the confirmed dose

### Requirement: Record verified badge
The system SHALL show a verified badge when the record's integrity check passes, and SHALL show it as broken, naming the altered turn, when any past turn is changed outside the review process.

#### Scenario: Tamper demonstration
- **WHEN** the presenter uses the hidden tamper control to alter a stored turn
- **THEN** the badge turns to broken and identifies the altered turn

### Requirement: Replay mode
The system SHALL be able to replay a recorded session through the same screens at its original pace without network access.

#### Scenario: Network down
- **WHEN** replay mode is started with the network disconnected
- **THEN** the screens show the recorded consultation as if live, and a small replay indicator is visible to the presenter
