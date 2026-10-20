# Spec Delta

## Purpose

Makes every sentence of an AI-drafted clinical note traceable to who said it in the consultation, or clearly marked as AI inference, so neither party can be misquoted.

## ADDED Requirements

### Requirement: Sentence-level source links
The system SHALL link every sentence of a generated clinical note to one or more transcript segments that support it.

#### Scenario: Following a link
- **WHEN** a reader selects a sentence in the note
- **THEN** the system highlights the supporting transcript segments and offers playback of the matching audio where audio is retained

### Requirement: Provenance tags
The system SHALL tag every note sentence with exactly one provenance: patient-stated, physician-stated, companion-stated, or AI inference.

#### Scenario: Symptom reported by the patient
- **WHEN** a note sentence records a symptom the patient described
- **THEN** the sentence is tagged patient-stated and linked to the patient's segment

#### Scenario: Assessment drawn by the model
- **WHEN** a note sentence is a conclusion not spoken by any participant
- **THEN** the sentence is tagged AI inference and visually distinguished from stated content

### Requirement: Inference is never quoted
The system SHALL NOT present AI inference as a direct quotation or attribute it to a participant.

#### Scenario: Unsupported sentence
- **WHEN** a generated sentence has no supporting segment
- **THEN** the system tags it AI inference and requires the physician to accept, edit, or remove it before sign-off

### Requirement: Provenance follows amendments
The system SHALL update note links and flag affected note sentences when a supporting segment is amended or reattributed.

#### Scenario: Patient amends a linked segment
- **WHEN** a segment that supports a note sentence is amended by the patient
- **THEN** the dependent note sentence is flagged for physician review

### Requirement: Physician as final author
The system SHALL require physician approval of the note before it is finalised or exported, and SHALL record the approving physician.

#### Scenario: Export before approval
- **WHEN** a user attempts to export a note the physician has not approved
- **THEN** the system refuses the export
