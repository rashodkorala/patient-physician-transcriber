# Spec Delta

## Purpose

Gives patients informed, granular, and revocable control over whether and how their consultation is recorded and processed by AI, so they can speak openly.

## ADDED Requirements

### Requirement: Consent before capture
The system SHALL NOT capture or process any consultation audio until the patient has given consent for that specific visit.

#### Scenario: No consent recorded
- **WHEN** a physician starts a visit for which no patient consent exists
- **THEN** the system refuses to start recording and prompts for patient consent

#### Scenario: Consent given
- **WHEN** the patient gives consent for the visit
- **THEN** the system records the consent with the patient identity, visit identifier, chosen scope, and timestamp, and allows recording to start

### Requirement: Granular consent scope
The system SHALL let the patient choose one consent scope per visit: full (audio retained, transcript, and AI note), transcript only (audio discarded after transcription), or no AI (no capture at all).

#### Scenario: Transcript-only scope
- **WHEN** the patient chooses transcript only
- **THEN** the system deletes the raw audio once the transcript is verified and records the deletion in the audit trail

#### Scenario: No-AI scope
- **WHEN** the patient chooses no AI
- **THEN** the system does not capture audio and the visit proceeds without AI documentation

### Requirement: Retention and sharing notice
The system SHALL show the patient, before consent, a plain-language statement of what is captured, who can access it, which third-party processors are used, and how long each item is retained.

#### Scenario: Notice shown before consent
- **WHEN** the consent screen is displayed
- **THEN** the retention and sharing statement is visible and the patient cannot consent without it having been presented

### Requirement: Off-the-record pause
The system SHALL let either participant pause capture at any time, and SHALL NOT capture or retain any audio while paused.

#### Scenario: Patient pauses for a sensitive disclosure
- **WHEN** the patient activates "off the record" during a visit
- **THEN** capture stops immediately, both participants see a visible paused indicator, and the transcript shows a marker for the paused interval with no content

#### Scenario: Resuming capture
- **WHEN** capture is resumed after a pause
- **THEN** the system resumes only after an explicit resume action and the indicator returns to recording

### Requirement: Consent revocation
The system SHALL let the patient revoke consent for a visit at any time, after which no further processing of that visit's data occurs except what law requires to retain.

#### Scenario: Revocation after the visit
- **WHEN** the patient revokes consent for a completed visit
- **THEN** the system deletes audio and transcript that are not legally required, stops any pending AI processing, records the revocation in the audit trail, and notifies the physician
