# Spec Delta

## Purpose

Turns consultation audio into a transcript in which every segment is attributed to a speaker role with a confidence score, so both parties can see who said what.

## ADDED Requirements

### Requirement: Speaker roles
The system SHALL attribute every transcript segment to exactly one speaker role: patient, physician, companion, or unknown.

#### Scenario: Two-party consultation
- **WHEN** a consultation between a patient and a physician is transcribed
- **THEN** every segment is labelled either patient or physician, or unknown where attribution is not possible

#### Scenario: Companion present
- **WHEN** a third person such as a carer or interpreter speaks during the visit
- **THEN** their segments are labelled companion and are distinguishable from the patient's

### Requirement: Segment timing and confidence
The system SHALL store, for every segment, its start and end time in the audio, its text, a transcription confidence score, and a speaker attribution confidence score.

#### Scenario: Segment metadata available
- **WHEN** a transcript is produced
- **THEN** each segment exposes its start time, end time, text, transcription confidence, and speaker confidence

### Requirement: Low-confidence flagging
The system SHALL flag any segment whose transcription or speaker confidence falls below a configurable threshold, and flagged segments SHALL require human review before the transcript can be finalised.

#### Scenario: Uncertain speaker
- **WHEN** a segment's speaker confidence is below the threshold
- **THEN** the segment is visibly flagged to both participants and the transcript cannot be finalised until the segment is confirmed or corrected

### Requirement: Transcript visible to both parties
The system SHALL make the speaker-attributed transcript of a visit available to both the patient and the physician of that visit.

#### Scenario: Patient views transcript
- **WHEN** the patient opens a visit they consented to record
- **THEN** they see the full transcript with speaker labels and paused-interval markers
