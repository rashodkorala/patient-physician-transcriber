# Spec Delta

## Purpose

Gives the patient a clear, warm, plain-language summary of their visit in their own language, so they understand the outcome and know their concerns were addressed.

## ADDED Requirements

### Requirement: Summary in the patient's language
The system SHALL generate a patient summary of each verified visit in the patient's visit language, covering what was discussed, any diagnosis or working assessment, the plan, medications, and next steps.

#### Scenario: Summary in Punjabi
- **WHEN** the physician signs off a visit in which the patient spoke Punjabi
- **THEN** a summary in Punjabi is generated for physician approval

### Requirement: Reading level, other languages, and audio
The system SHALL let the patient choose the summary's reading level, view it in any other supported language, and listen to it read aloud.

#### Scenario: Family member reads in English
- **WHEN** the patient switches the summary to English
- **THEN** the summary is shown in English with the same clinical content

#### Scenario: Patient cannot read
- **WHEN** the patient selects listen
- **THEN** the summary is read aloud in their language

### Requirement: Critical values match the record
The system SHALL ensure that every number, dose, unit, frequency, date, and medication name in the summary matches the verified record exactly.

#### Scenario: Dose in summary
- **WHEN** the verified record says 500 milligrams twice a day
- **THEN** the summary states the same dose and frequency, and generation fails rather than releasing a summary with a mismatched value

### Requirement: Questions answered list
The system SHALL list every question the patient asked during the visit alongside the answer given, in the patient's language, and SHALL mark questions with no identifiable answer.

#### Scenario: Unanswered question
- **WHEN** a patient question has no answering segment in the transcript
- **THEN** the summary marks it as not answered and offers a way to send it to the physician, which is translated for them

### Requirement: Summary traceability
The system SHALL link each summary statement to its source note sentence or transcript segment, and SHALL distinguish statements drawn from AI inference.

#### Scenario: Patient checks a statement
- **WHEN** the patient selects a statement in their summary
- **THEN** the system shows the supporting part of the transcript in the patient's language

### Requirement: Physician review of summary
The system SHALL require physician approval of the patient summary before release, showing the physician a back-translation into their own language.

#### Scenario: Summary awaiting approval
- **WHEN** a summary has been generated but not approved
- **THEN** the patient sees, in their language, that the summary is pending and cannot view its content
