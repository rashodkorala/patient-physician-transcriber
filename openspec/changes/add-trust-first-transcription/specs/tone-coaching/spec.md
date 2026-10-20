# Spec Delta

## Purpose

Gives physicians private, opt-in feedback on how they communicated during a visit, so patients feel heard and are more willing to speak openly.

## ADDED Requirements

### Requirement: Opt-in and private
The system SHALL generate tone feedback only for physicians who have opted in, and SHALL show it only to that physician unless they explicitly choose to share it.

#### Scenario: Physician not opted in
- **WHEN** a visit is completed by a physician who has not opted in
- **THEN** no tone feedback is generated

#### Scenario: Access by another user
- **WHEN** anyone other than the physician requests that physician's tone feedback without a share grant
- **THEN** the system denies access

### Requirement: Post-visit tone summary
The system SHALL produce, after each visit, a tone summary covering interruptions of the patient, medical jargon not explained, patient questions left unanswered, and the share of speaking time per participant.

#### Scenario: Summary contents
- **WHEN** an opted-in physician opens the tone summary for a visit
- **THEN** they see counts and examples for each covered signal, each linked to the transcript moment it refers to

### Requirement: Evidence-linked feedback
The system SHALL link every tone observation to the transcript segments it is based on.

#### Scenario: Checking an observation
- **WHEN** the physician selects an observation such as "jargon not explained"
- **THEN** the system shows the segment where the term was used

### Requirement: Feedback excluded from the record
The system SHALL keep tone feedback out of the clinical note, the patient summary, and any export of the medical record.

#### Scenario: Note export
- **WHEN** a clinical note is exported
- **THEN** the export contains no tone feedback
