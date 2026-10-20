# Spec Delta

## Purpose

Turns consultation audio into a bilingual transcript in which every segment is attributed to a speaker role and keeps both the original speech and its translation, so both parties can see who said what in each language.

## ADDED Requirements

### Requirement: Speaker roles
The system SHALL attribute every transcript segment to exactly one speaker role: patient, physician, companion, interpreter, or unknown.

#### Scenario: Two-party consultation
- **WHEN** a consultation between a patient and a physician is transcribed
- **THEN** every segment is labelled either patient or physician, or unknown where attribution is not possible

#### Scenario: Companion present
- **WHEN** a third person such as a carer speaks during the visit
- **THEN** their segments are labelled companion and are distinguishable from the patient's

#### Scenario: Human interpreter present
- **WHEN** a human interpreter joins by phone or video
- **THEN** their segments are labelled interpreter

### Requirement: Bilingual segments
The system SHALL store, for every segment, the detected spoken language, the original-language text, and the translation into the other visit language.

#### Scenario: Patient speaks Tamil
- **WHEN** the patient speaks Tamil in a Tamil and English visit
- **THEN** the segment stores language Tamil, the Tamil text, and the English translation

#### Scenario: Unexpected language
- **WHEN** a speaker uses a language other than the two visit languages
- **THEN** the segment records the detected language and is flagged for review

### Requirement: Segment timing and confidence
The system SHALL store, for every segment, its start and end time in the audio, a speech recognition confidence, a translation confidence, and a speaker attribution confidence.

#### Scenario: Segment metadata available
- **WHEN** a transcript is produced
- **THEN** each segment exposes its start time, end time, language, original text, translation, and all three confidence scores

### Requirement: Low-confidence flagging
The system SHALL flag any segment whose recognition, translation, or speaker confidence falls below the threshold for its language tier, and flagged segments SHALL require human review before the transcript can be finalised.

#### Scenario: Uncertain translation
- **WHEN** a segment's translation confidence is below the tier threshold
- **THEN** the segment is visibly flagged to both participants and the transcript cannot be finalised until it is confirmed or corrected

### Requirement: Transcript visible to both parties
The system SHALL make the bilingual transcript of a visit available to both the patient and the physician, with each viewer able to choose which language is shown first.

#### Scenario: Patient views transcript
- **WHEN** the patient opens a visit they consented to record
- **THEN** they see every segment with speaker label, their language shown first, the other language alongside, and paused-interval markers
