# Spec Delta

## Purpose

Gives the patient a clear, warm, plain-language summary of their visit in their own language, so they understand the outcome and know their concerns were addressed.

## ADDED Requirements

### Requirement: Plain-language summary
The system SHALL generate a patient summary of each verified visit covering what was discussed, any diagnosis or working assessment, the plan, medications, and next steps.

#### Scenario: Summary available after sign-off
- **WHEN** the physician signs off a visit
- **THEN** a patient summary is generated and made available to the patient

### Requirement: Reading level and language
The system SHALL let the patient choose the summary's language and reading level, and SHALL regenerate the summary on request.

#### Scenario: Patient changes language
- **WHEN** the patient selects a different supported language
- **THEN** the summary is presented in that language with the same clinical content

### Requirement: Questions answered list
The system SHALL list every question the patient asked during the visit alongside the answer given, and SHALL mark questions with no identifiable answer.

#### Scenario: Unanswered question
- **WHEN** a patient question has no answering segment in the transcript
- **THEN** the summary marks it as not answered and offers a way to send it to the physician

### Requirement: Summary traceability
The system SHALL link each summary statement to its source note sentence or transcript segment, and SHALL distinguish statements drawn from AI inference.

#### Scenario: Patient checks a statement
- **WHEN** the patient selects a statement in their summary
- **THEN** the system shows the supporting part of the transcript or note

### Requirement: Physician review of summary
The system SHALL require physician approval of the patient summary before it is released to the patient.

#### Scenario: Summary awaiting approval
- **WHEN** a summary has been generated but not approved
- **THEN** the patient sees that the summary is pending and cannot view its content
