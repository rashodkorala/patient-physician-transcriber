# Spec Delta

## Purpose

Gives patients informed, granular, and revocable control, in their own language, over whether and how their consultation is interpreted, recorded, and processed by AI, so they can speak openly.

## ADDED Requirements

### Requirement: Consent in the patient's language
The system SHALL present the consent request, scope options, and retention notice in the patient's selected language, as text and, on request, as spoken audio.

#### Scenario: Consent in Tagalog
- **WHEN** the patient's language is Tagalog
- **THEN** the consent screen and retention notice are shown in Tagalog and can be read aloud in Tagalog

#### Scenario: Language not yet chosen
- **WHEN** the consent screen opens before a language is chosen
- **THEN** the patient can pick their language from a list shown in each language's own script before any consent text is shown

### Requirement: Consent before capture
The system SHALL NOT capture or process any consultation audio until the patient has given consent for that specific visit.

#### Scenario: No consent recorded
- **WHEN** a physician starts a visit for which no patient consent exists
- **THEN** the system refuses to start capture and prompts for patient consent

#### Scenario: Consent given
- **WHEN** the patient gives consent for the visit
- **THEN** the system records the consent with patient identity, visit identifier, chosen scope, language of the notice shown, and timestamp, and allows capture to start

### Requirement: Granular consent scope
The system SHALL let the patient choose one consent scope per visit: interpret and record (audio retained, transcript, and AI note), interpret with transcript only (audio discarded after verification), interpret only (live interpretation with nothing retained), or no AI.

#### Scenario: Interpret only
- **WHEN** the patient chooses interpret only
- **THEN** the system provides live interpretation and retains no audio, transcript, or note after the visit ends

#### Scenario: No AI
- **WHEN** the patient chooses no AI
- **THEN** the system does not capture audio and offers to connect a human interpreter

### Requirement: Capabilities follow the consent scope
The system SHALL enable other capabilities only as the visit's scope allows: full scope enables all; transcript only enables all except audio playback; interpret only enables live interpretation and captions; no AI enables only human interpreter hand-off. Both keep audit entries for consent, interpreter hand-off, and access, none holding content. The matrix in design.md is normative.

#### Scenario: Interpret-only visit ends
- **WHEN** a visit with the interpret-only scope ends
- **THEN** no transcript review, clinical note, patient summary, coaching feedback, or verify-my-copy is offered, and only consent, interpreter hand-off, and access events remain in the audit trail, with no content

#### Scenario: Transcript-only note
- **WHEN** a physician follows a note sentence's source in a transcript-only visit
- **THEN** the source transcript text is shown and no audio playback is offered

### Requirement: Retention and sharing notice
The system SHALL show the patient, before consent, a plain-language statement of what is captured, who can access it, which processors are used, where data is stored, and how long each item is retained.

#### Scenario: Notice shown before consent
- **WHEN** the consent screen is displayed
- **THEN** the retention and sharing statement is visible in the patient's language and the patient cannot consent without it having been presented

### Requirement: Off-the-record pause
The system SHALL let either participant pause capture at any time, and SHALL NOT capture or retain any audio while paused.

#### Scenario: Patient pauses for a sensitive disclosure
- **WHEN** the patient activates "off the record" during a visit
- **THEN** capture stops immediately, the shared screen shows a paused notice in both languages, and the transcript shows a marker for the paused interval with no content

#### Scenario: Resuming capture
- **WHEN** capture is resumed after a pause
- **THEN** the system resumes only after an explicit resume action and the shared screen shows that capture is active again

### Requirement: Consent revocation
The system SHALL let the patient revoke consent for a visit at any time, after which no further processing of that visit's data occurs except what law requires to retain.

#### Scenario: Revocation after the visit
- **WHEN** the patient revokes consent for a completed visit
- **THEN** the system deletes audio and transcript that are not legally required, stops any pending AI processing, records the revocation in the audit trail, and notifies the physician

#### Scenario: Revocation keeps a fingerprint tombstone
- **WHEN** content is deleted after revocation
- **THEN** the audit trail keeps a tombstone entry with the content fingerprint but no content, so the chain still verifies
