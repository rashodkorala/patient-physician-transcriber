## ADDED Requirements

### Requirement: Hands-free mode
The system SHALL let the physician switch the controller between push-to-talk and hands-free listening, with push-to-talk as the default.

#### Scenario: Turning hands-free on
- **WHEN** the physician turns hands-free on
- **THEN** the controller listens continuously and shows that it is listening

#### Scenario: Language without support
- **WHEN** the visit's patient language cannot be identified automatically
- **THEN** hands-free cannot be turned on and push-to-talk remains available

### Requirement: Speaker found by spoken language
The system SHALL record each hands-free turn with the speaker whose language was spoken: the physician for the physician's language and the patient for the patient's language.

#### Scenario: Patient speaks
- **WHEN** hands-free is on and the patient speaks Punjabi, then pauses
- **THEN** a turn is recorded with speaker patient and language Punjabi

#### Scenario: Physician speaks
- **WHEN** hands-free is on and the physician speaks English, then pauses
- **THEN** a turn is recorded with speaker physician and language English

### Requirement: The interpreter does not hear itself
The system SHALL NOT record a turn from audio captured while a translation or interpreter line is being spoken aloud.

#### Scenario: Translation plays
- **WHEN** a physician turn's translation is spoken aloud in Punjabi
- **THEN** no patient turn is recorded from that spoken translation

### Requirement: Pauses during confirmation and override
The system SHALL stop hands-free listening while a dose read-back is waiting for confirmation and while a push-to-talk control is held, and resume afterwards.

#### Scenario: Push-to-talk override
- **WHEN** hands-free is on and the physician holds the patient control
- **THEN** the utterance is recorded as a patient turn, as in push-to-talk, and hands-free listening resumes on release

### Requirement: Speaker correction
The system SHALL show the physician which speaker each hands-free turn was given, and SHALL let the physician correct it in one action.

#### Scenario: Wrong speaker
- **WHEN** a patient answers in English and the turn is recorded as physician
- **THEN** the physician can mark it as the patient's, and the turn is recorded again with speaker patient while the mislabelled turn is discarded
