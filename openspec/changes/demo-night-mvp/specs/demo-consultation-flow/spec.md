# Spec Delta

## Purpose

Demonstrates, live on demo night, a consultation between a patient and a physician who do not share a language: tone-aware interpretation on a shared screen, safety checks, and a record both parties can verify.

## ADDED Requirements

### Requirement: Language selection
The system SHALL list the thirteen roadmap languages in their own scripts and SHALL allow Punjabi and French as live patient languages with English as the physician language, marking the others as coming soon.

#### Scenario: Choosing Punjabi
- **WHEN** the physician selects Punjabi as the patient language
- **THEN** the visit is set to interpret between Punjabi and English

#### Scenario: Unavailable language
- **WHEN** a user selects a language marked coming soon
- **THEN** the system explains it is not available in this demo and keeps the current selection

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
The system SHALL show each turn on the shared screen with the speaker label, the original text, and the translation side by side, readable from across the room.

#### Scenario: Caption appears
- **WHEN** a turn's translation is ready
- **THEN** the shared screen shows speaker, original, and translation together within 3 seconds of the end of speech in normal conditions

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
The system SHALL show a tone label on each caption (for example reassuring, respectful, or empathetic).

#### Scenario: Label shown
- **WHEN** a caption appears on the shared screen
- **THEN** it carries at least one tone label

### Requirement: Empathy nudge
The system SHALL show the physician, and only the physician, a suggestion with a ready phrase when a patient turn expresses worry, embarrassment, pain, or confusion.

#### Scenario: Worried patient
- **WHEN** the patient says they are scared about the cost of medication
- **THEN** the physician's controller shows a nudge to acknowledge the worry with a suggested phrase, and the shared screen does not show it

### Requirement: Critical value read-back
The system SHALL detect numbers, doses, units, frequencies, dates, and medication names in a physician turn, highlight them in both languages, and require the physician to confirm them before the translation is spoken.

#### Scenario: Dose confirmed
- **WHEN** the physician says "take 500 milligrams twice a day" and confirms the highlighted values
- **THEN** the translation is spoken and the values appear highlighted on the shared screen

#### Scenario: Mismatch blocked
- **WHEN** a critical value in the translation does not match the original
- **THEN** the translation is not spoken and the physician is asked to repeat

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
The system SHALL offer a human interpreter when a turn's confidence is low after one retry, and SHALL let either party request one at any time, showing a connecting state in both languages.

#### Scenario: Low confidence
- **WHEN** a translation fails verification twice
- **THEN** the turn is marked uncertain and a human interpreter is offered in both languages

#### Scenario: Requested
- **WHEN** the patient presses the human interpreter button
- **THEN** a connecting state is shown and the request is recorded in the transcript

### Requirement: Transcript review
The system SHALL show the bilingual, speaker-labelled transcript after the visit, and SHALL let the patient confirm or correct their own turns while keeping the original text.

#### Scenario: Patient corrects a turn
- **WHEN** the patient re-speaks a correction for one of their turns
- **THEN** the turn shows the correction and its translation, and the original remains visible in its history

### Requirement: Note with provenance tags
The system SHALL generate an English clinical note in which every sentence is tagged patient-said, physician-said, or AI inference and links to its source turns.

#### Scenario: Following a source
- **WHEN** the physician selects a note sentence tagged patient-said
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
