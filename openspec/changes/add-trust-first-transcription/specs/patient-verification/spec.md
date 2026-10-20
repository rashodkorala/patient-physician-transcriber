# Spec Delta

## Purpose

Lets the patient and the physician each verify their own words in the transcript, so the final record is jointly confirmed and disagreements are preserved openly.

## ADDED Requirements

### Requirement: Patient review of own statements
The system SHALL let the patient confirm or correct each segment attributed to them, and SHALL let them add clarifying context to any segment.

#### Scenario: Patient confirms a segment
- **WHEN** the patient marks one of their segments as accurate
- **THEN** the segment is recorded as patient-confirmed with a timestamp

#### Scenario: Patient corrects a segment
- **WHEN** the patient edits the text of one of their segments
- **THEN** the system stores the correction as an amendment linked to the original segment and marks the segment as patient-amended

### Requirement: Speaker reattribution request
The system SHALL let either participant dispute the speaker label of any segment.

#### Scenario: Wrong speaker label
- **WHEN** the patient reports that a segment labelled patient was spoken by the physician
- **THEN** the segment is marked disputed and shown to the physician for resolution

### Requirement: Physician sign-off
The system SHALL require the physician to review their own segments, all disputed segments, and all patient amendments before signing off the transcript.

#### Scenario: Sign-off blocked by open dispute
- **WHEN** the physician attempts to sign off while a disputed segment is unresolved
- **THEN** the system blocks sign-off and lists the unresolved segments

#### Scenario: Physician disagrees with an amendment
- **WHEN** the physician does not accept a patient amendment
- **THEN** both versions are kept side by side, labelled with their author, and the disagreement is visible to both parties

### Requirement: Originals are never overwritten
The system SHALL preserve the original transcribed text of every segment regardless of later corrections, amendments, or reattributions.

#### Scenario: Viewing history
- **WHEN** either participant opens a segment's history
- **THEN** they see the original text, every amendment, its author, and its timestamp in order

### Requirement: Verification status
The system SHALL show a verification status for each visit: awaiting patient review, awaiting physician sign-off, verified by both, or verified with disagreements.

#### Scenario: Fully verified visit
- **WHEN** the patient has completed review and the physician has signed off with no outstanding disagreements
- **THEN** the visit status is verified by both

### Requirement: Review window
The system SHALL give the patient a configurable review window after the visit, and SHALL record when the window closes without patient review.

#### Scenario: Patient does not review
- **WHEN** the review window ends with no patient action
- **THEN** the visit is marked as not patient-reviewed, and the patient can still submit amendments later through the right-to-amend process
