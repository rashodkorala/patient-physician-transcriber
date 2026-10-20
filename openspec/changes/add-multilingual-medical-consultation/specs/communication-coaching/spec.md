# Spec Delta

## Purpose

Gives physicians private, opt-in feedback on how well they communicated across the language barrier, so meaning, warmth, and certainty survive translation and patients feel heard.

## ADDED Requirements

### Requirement: Opt-in and private
The system SHALL generate communication feedback only for physicians who have opted in, and SHALL show it only to that physician unless they explicitly choose to share it.

#### Scenario: Physician not opted in
- **WHEN** a visit is completed by a physician who has not opted in
- **THEN** no communication feedback is generated

#### Scenario: Access by another user
- **WHEN** anyone other than the physician requests that physician's feedback without a share grant
- **THEN** the system denies access

### Requirement: Translation-aware feedback
The system SHALL report, after each visit, the physician utterances that translated poorly, including idioms, unexplained jargon, ambiguous pronouns, and long multi-instruction sentences, with a suggested simpler phrasing.

#### Scenario: Idiom used
- **WHEN** the physician said "we will keep an eye on it" and the translation was low confidence or literal
- **THEN** the feedback shows the utterance, its translation, and a plainer alternative such as "we will check it again in two weeks"

### Requirement: Lost tone signals
The system SHALL report where warmth, reassurance, or certainty in the physician's words was weakened or changed in translation, by comparing the physician's original with a back-translation.

#### Scenario: Certainty changed
- **WHEN** the physician said "this is very unlikely to be serious" and the back-translation reads as "this might be serious"
- **THEN** the feedback flags the change in certainty and links to the segment

### Requirement: Misunderstanding signals
The system SHALL report signs that the patient did not understand, including repeated questions, failed comprehension checks, unanswered patient questions, and interruptions of the patient.

#### Scenario: Repeated question
- **WHEN** the patient asked the same question more than once in the visit
- **THEN** the feedback lists the question and the answers given

### Requirement: Speaking balance
The system SHALL report the share of speaking time per participant.

#### Scenario: Balance shown
- **WHEN** an opted-in physician opens feedback for a visit
- **THEN** they see the share of speaking time for each participant

### Requirement: Evidence-linked feedback
The system SHALL link every feedback item to the transcript segments it is based on.

#### Scenario: Checking an item
- **WHEN** the physician selects a feedback item
- **THEN** the system shows the original and translated text of the segment it refers to

### Requirement: Feedback excluded from the record
The system SHALL keep communication feedback out of the clinical note, the patient summary, and any export of the medical record.

#### Scenario: Note export
- **WHEN** a clinical note is exported
- **THEN** the export contains no communication feedback
