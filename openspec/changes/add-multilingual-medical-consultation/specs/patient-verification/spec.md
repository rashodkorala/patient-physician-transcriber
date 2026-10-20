# Spec Delta

## Purpose

Lets the patient and the physician each verify their own words, and how they were translated, in their own language, so the final record is jointly confirmed and disagreements are preserved openly.

## ADDED Requirements

### Requirement: Patient review in their own language
The system SHALL present the patient's review entirely in the patient's language, showing for each of their segments what they said and how it was translated back into their language.

#### Scenario: Reviewing a translated statement
- **WHEN** the patient opens one of their segments for review
- **THEN** they see their original words and a back-translation of the physician-language text into their own language, so they can judge whether the meaning was kept

### Requirement: Patient confirmation and correction
The system SHALL let the patient confirm, correct, or add context to each segment attributed to them, in their own language.

#### Scenario: Patient confirms a segment
- **WHEN** the patient marks one of their segments as accurate
- **THEN** the segment is recorded as patient-confirmed with a timestamp

#### Scenario: Patient corrects the meaning
- **WHEN** the patient reports that the translation of their segment changed its meaning and enters a correction in their language
- **THEN** the system stores the correction and its new translation as an amendment linked to the original segment and marks the segment as patient-amended

### Requirement: Physician review of translations
The system SHALL let the physician confirm or correct segments attributed to them, viewing the translation the patient received through a back-translation into the physician's language.

#### Scenario: Physician finds a mistranslation
- **WHEN** the physician sees that the back-translation of an instruction differs from what they meant
- **THEN** they can amend the segment and the system flags it so the corrected translation is sent to the patient

### Requirement: Speaker reattribution request
The system SHALL let either participant dispute the speaker label of any segment.

#### Scenario: Wrong speaker label
- **WHEN** the patient reports that a segment labelled patient was spoken by a companion
- **THEN** the segment is marked disputed and shown to the physician for resolution

### Requirement: Physician sign-off
The system SHALL require the physician to review their own segments, all disputed segments, and all patient amendments before signing off the transcript.

#### Scenario: Sign-off blocked by open dispute
- **WHEN** the physician attempts to sign off while a disputed segment is unresolved
- **THEN** the system blocks sign-off and lists the unresolved segments

#### Scenario: Physician disagrees with an amendment
- **WHEN** the physician does not accept a patient amendment
- **THEN** both versions are kept side by side in both languages, labelled with their author, and the disagreement is visible to both parties

### Requirement: Originals are never overwritten
The system SHALL preserve the original-language text and original translation of every segment regardless of later corrections, amendments, or reattributions.

#### Scenario: Viewing history
- **WHEN** either participant opens a segment's history
- **THEN** they see the original text, the original translation, every amendment, its author, and its timestamp in order

### Requirement: Verification status
The system SHALL show a verification status for each visit, in each viewer's language: awaiting patient review, awaiting physician sign-off, verified by both, or verified with disagreements.

#### Scenario: Fully verified visit
- **WHEN** the patient has completed review and the physician has signed off with no outstanding disagreements
- **THEN** the visit status is verified by both

### Requirement: Review window
The system SHALL give the patient a configurable review window after the visit, and SHALL record when the window closes without patient review.

#### Scenario: Patient does not review
- **WHEN** the review window ends with no patient action
- **THEN** the visit is marked as not patient-reviewed, and the patient can still submit amendments later through the right-to-correct process
