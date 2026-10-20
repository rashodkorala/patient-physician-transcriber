# Spec Delta

## Purpose

Guarantees that transcripts, amendments, sign-offs, and accesses cannot be altered or hidden without detection, and lets the patient see who has accessed their record.

## ADDED Requirements

### Requirement: Append-only audit trail
The system SHALL record every consent event, transcript creation, amendment, reattribution, sign-off, export, deletion, and access as an append-only audit entry with actor, action, target, and timestamp.

#### Scenario: Amendment recorded
- **WHEN** a patient amends a segment
- **THEN** an audit entry is appended identifying the patient, the segment, and the time

### Requirement: Tamper evidence
The system SHALL chain audit entries cryptographically so that any modification or removal of a past entry is detectable.

#### Scenario: Integrity check passes
- **WHEN** an integrity check runs over an unmodified audit trail
- **THEN** the check reports the trail as intact

#### Scenario: Integrity check detects tampering
- **WHEN** any past audit entry has been altered or deleted
- **THEN** the integrity check reports the trail as broken and identifies the first inconsistent entry

### Requirement: Verifiable finalised record
The system SHALL compute a content fingerprint for each finalised transcript and note, and SHALL let either participant verify that a copy they hold matches the stored record.

#### Scenario: Patient verifies a downloaded copy
- **WHEN** the patient submits a previously downloaded transcript for verification
- **THEN** the system reports whether it matches the finalised record

### Requirement: Patient-visible access log
The system SHALL show the patient a list of every person and system that viewed, exported, or processed their visit data, with role and time.

#### Scenario: Viewing the access log
- **WHEN** the patient opens the access log for a visit
- **THEN** they see each access with the accessor's name or system, role, action, and timestamp

### Requirement: Encryption
The system SHALL encrypt all audio, transcripts, notes, and audit data in transit and at rest.

#### Scenario: Storage inspection
- **WHEN** stored visit data is read directly from the storage layer without application keys
- **THEN** the content is unreadable
