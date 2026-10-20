# Spec Delta

## Purpose

Makes every sentence of an AI-drafted clinical note traceable to who said it, in which language, and how it was translated, or clearly marked as AI inference, so neither party can be misquoted across the language barrier.

## ADDED Requirements

### Requirement: Note language
The system SHALL write the clinical note in the physician's chosen record language, English or French.

#### Scenario: French record
- **WHEN** the physician's record language is French and the patient spoke Arabic
- **THEN** the note is written in French

### Requirement: Sentence-level source links
The system SHALL link every sentence of a generated clinical note to one or more transcript segments that support it, including the original-language text and its translation.

#### Scenario: Following a link
- **WHEN** a reader selects a note sentence based on something the patient said in Cantonese
- **THEN** the system shows the Cantonese original, its translation, and offers playback of the matching audio where audio is retained

### Requirement: Provenance tags
The system SHALL tag every note sentence with exactly one provenance: patient-stated, physician-stated, companion-stated, interpreter-stated, or AI inference.

#### Scenario: Symptom reported by the patient
- **WHEN** a note sentence records a symptom the patient described
- **THEN** the sentence is tagged patient-stated and linked to the patient's segment

#### Scenario: Assessment drawn by the model
- **WHEN** a note sentence is a conclusion not spoken by any participant
- **THEN** the sentence is tagged AI inference and visually distinguished from stated content

### Requirement: Translation uncertainty carried into the note
The system SHALL mark any note sentence whose supporting segments were flagged for low translation confidence until those segments are verified.

#### Scenario: Unverified translation behind a note sentence
- **WHEN** a note sentence relies on a segment with an unresolved translation flag
- **THEN** the note shows the sentence as translation-unverified and the physician must resolve it before sign-off

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
