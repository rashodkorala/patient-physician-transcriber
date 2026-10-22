# Spec Delta

## Purpose

Lets a patient and a physician who do not share a language understand each other in real time during a consultation, safely enough for clinical use, with a human interpreter available when AI is not.

## ADDED Requirements

### Requirement: Language selection
The system SHALL let the patient's language and the physician's language be chosen at the start of a visit from the supported language list, and SHALL let either be changed during the visit.

#### Scenario: Patient chooses their language
- **WHEN** a visit starts and the patient selects Punjabi while the physician's language is English
- **THEN** the system interprets between Punjabi and English for the rest of the visit

#### Scenario: Shared language
- **WHEN** the patient's language and the physician's language are the same
- **THEN** the system runs in transcription-only mode without translation

### Requirement: Supported languages
The system SHALL support English, French, Mandarin, Cantonese, Punjabi, Urdu, Arabic, Farsi, Tagalog, Spanish, Portuguese, Sinhala, and Tamil as both patient and physician languages.

#### Scenario: Language list
- **WHEN** a user opens the language selector
- **THEN** all thirteen languages are offered, each shown in its own script and name

### Requirement: Two-way live interpretation
The system SHALL translate each utterance from the speaker's language into the listener's language, and SHALL both speak the translation aloud and show it on screen.

#### Scenario: Physician speaks
- **WHEN** the physician finishes an utterance in English during a Mandarin and English visit
- **THEN** the Mandarin translation is spoken aloud and shown on the shared screen

#### Scenario: Patient speaks
- **WHEN** the patient finishes an utterance in Mandarin
- **THEN** the English translation is spoken aloud and shown on the shared screen

### Requirement: Shared bilingual screen
The system SHALL show the live conversation on a large shared display with each utterance in its original language and its translation side by side, labelled by speaker, readable from across a consulting room.

#### Scenario: Both parties read along
- **WHEN** an utterance is translated
- **THEN** the display shows the speaker label, the original text, and the translated text together, in the correct script and reading direction for each language

#### Scenario: Right-to-left language
- **WHEN** the patient's language is Arabic, Urdu, or Farsi
- **THEN** that language's text is rendered right to left while the other language keeps its own direction

### Requirement: Paused state on screen
The system SHALL show on the shared display, in both languages, when capture is paused, and SHALL show no captions while paused.

#### Scenario: Off the record
- **WHEN** either participant pauses capture
- **THEN** the display shows a paused notice in both languages and no new captions appear until capture resumes

### Requirement: Medical glossary
The system SHALL translate clinical terms using a maintained medical glossary for each supported language pair, and SHALL show a plain-language explanation alongside technical terms in the patient's language.

#### Scenario: Technical term
- **WHEN** the physician says "hypertension"
- **THEN** the patient's translation uses the glossary term for the patient's language and the display shows a plain-language explanation beside it

### Requirement: Read-back of critical values
The system SHALL detect numbers, doses, units, frequencies, dates, and medication names in a physician utterance, highlight them in both languages, and SHALL NOT speak or show the translation until the physician confirms them. No automated check can stand in for this confirmation.

#### Scenario: Dose instruction
- **WHEN** the physician says "take 500 milligrams twice a day"
- **THEN** the physician sees the dose, unit, and frequency highlighted in both languages, and the translation is spoken only after the physician confirms them

#### Scenario: Correction during read-back
- **WHEN** the speaker rejects a highlighted value during read-back
- **THEN** the system discards that translation and asks the speaker to repeat the utterance

### Requirement: Critical value mismatch blocks speech
The system SHALL, on any turn, re-translate once when a critical value in the translation does not match the original, and SHALL block the turn if a value still does not match. A blocked turn SHALL never be spoken or shown on a shared screen.

#### Scenario: Mismatch blocked
- **WHEN** a dose still does not match the original after one re-translation
- **THEN** nothing is spoken, the physician sees the mismatched values, and the speaker is asked to repeat or rephrase

### Requirement: Turn outcome precedence
The system SHALL give each turn one outcome, choosing in this order: blocked, then escalated, then read-back, then final. A turn whose critical values match but whose confidence or tone check fails SHALL be escalated, never read back or spoken.

#### Scenario: Matched dose with failed tone check
- **WHEN** a dose matches but the tone check fails after one retry
- **THEN** the turn is escalated and the dose is not offered for read-back

### Requirement: Comprehension check
The system SHALL let the physician start a comprehension check in which the patient explains the plan back in their own language, and SHALL show the physician the translation alongside the original instructions.

#### Scenario: Plan explained back
- **WHEN** the physician starts a comprehension check after giving instructions
- **THEN** the patient is prompted in their language to explain the plan, and the physician sees the translated explanation next to the instructions it should match

#### Scenario: Mismatch detected
- **WHEN** the patient's explanation omits or contradicts a critical value from the instructions
- **THEN** the system flags the mismatch to the physician

### Requirement: Language quality tiers
The system SHALL assign each supported language a quality tier based on measured translation accuracy for medical content, and SHALL apply that tier's confidence threshold and escalation rules.

#### Scenario: Lower-tier language
- **WHEN** a visit uses a language in a lower quality tier
- **THEN** the system applies the stricter threshold for that tier and tells both parties, in their languages, that a human interpreter is available

### Requirement: Low-confidence escalation
The system SHALL offer a human interpreter whenever translation or speech recognition confidence for an utterance falls below the tier threshold.

#### Scenario: Uncertain translation
- **WHEN** an utterance's translation confidence falls below the threshold
- **THEN** the translation is not spoken or shown as final, the display shows that the turn is uncertain in both languages, and a human interpreter is offered

### Requirement: High-risk escalation
The system SHALL let the physician mark the visit or a moment as high risk (for example consent to a procedure, a serious diagnosis, end-of-life care, a mental health crisis, or a safeguarding concern), and SHALL then offer a human interpreter and record the mark. Automatic detection of such moments is not specified until ADR-008 is decided.

#### Scenario: Consent to a procedure
- **WHEN** the physician marks the moment as high risk before explaining a procedure that needs informed consent
- **THEN** the system offers a human interpreter in both languages before consent is taken and records the mark in the transcript

### Requirement: Human interpreter hand-off
The system SHALL let either participant request a human interpreter at any time, SHALL connect a qualified interpreter for the patient's language by phone or video, and SHALL record the hand-off in the transcript and audit trail.

#### Scenario: Patient requests a human
- **WHEN** the patient presses the human interpreter button
- **THEN** the system starts a connection to a qualified interpreter, shows the connection status on screen in both languages, and records the request

#### Scenario: Human interpreter joins
- **WHEN** a human interpreter is connected
- **THEN** the interpreter's segments are labelled interpreter in the transcript and AI translation is shown as secondary

### Requirement: Companion interpreting is flagged
The system SHALL record when a family member or companion interprets for the patient and SHALL offer AI or human interpretation instead. If the visit continues with the companion interpreting, the physician SHALL choose a reason (patient preference, urgent, or other). The visit is never blocked.

#### Scenario: Adult companion continues
- **WHEN** the physician indicates an adult companion is interpreting and continues with them
- **THEN** the system records the companion as interpreter, the offer of alternatives, and the physician's reason in the transcript

#### Scenario: Child interpreting
- **WHEN** the physician indicates the companion interpreting is a child
- **THEN** the system offers AI or a human interpreter, and continuing with the child requires the physician to record a reason, which is shown in the transcript
