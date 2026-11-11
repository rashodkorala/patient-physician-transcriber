# Spec Delta

## Purpose

Carries how the physician said something, not only what, so the patient hears and reads the care in the physician's words; and conveys the patient's affect to the physician through the interpreter's voice without exposing it to the room.

## ADDED Requirements

### Requirement: Manner read from the words
The system SHALL assign every turn one manner from a fixed set (plain, warm, reassuring, gentle, serious, urgent, apologetic, encouraging), read from the words said, defaulting to plain.

#### Scenario: Reassurance
- **WHEN** the physician says the tests were reassuring and the patient did not have a heart attack
- **THEN** the turn's manner is reassuring

#### Scenario: Plain information
- **WHEN** the physician asks how long the symptoms have lasted
- **THEN** the turn's manner is plain

### Requirement: Manner in the interpreter's voice
The system SHALL deliver a physician turn's spoken translation in that turn's manner, and SHALL deliver a patient or companion turn's spoken translation in a way that conveys the speaker's emotion to the physician.

#### Scenario: Urgent instruction
- **WHEN** a physician turn with manner urgent is spoken
- **THEN** the voice is given an urgent delivery

#### Scenario: Worried patient conveyed
- **WHEN** a worried patient turn is spoken to the physician
- **THEN** the voice is given a concerned delivery

### Requirement: Manner label for the physician's words
The system SHALL show, beneath the translation of every spoken physician turn whose manner is not plain, a label in the patient's language stating how it was said, with the English label for the physician, and SHALL show no manner or emotion label on any patient or companion caption.

#### Scenario: Gentle label
- **WHEN** a physician turn with manner gentle is spoken to a Punjabi patient
- **THEN** the shared screen and the patient's device show, in Punjabi, that it was said gently, and the shared screen also shows the English label

#### Scenario: No label on the patient's words
- **WHEN** a patient turn is spoken
- **THEN** its caption carries no manner or emotion label on any screen

### Requirement: Manner never changes meaning
The system SHALL keep every instruction, certainty, and critical value unchanged whatever the manner, and a manner word MAY appear only once, inside the reporting frame.

#### Scenario: Dose with a gentle manner
- **WHEN** the physician gently gives a dose of 0.4 milligrams
- **THEN** the relay keeps 0.4 milligrams, the critical value check passes as before, and any manner word sits only in the opening frame

#### Scenario: Frame adverb accepted by the tone check
- **WHEN** a relay adds only "gently" to the reporting frame of an otherwise faithful translation
- **THEN** the tone check passes and the turn is not escalated

### Requirement: Manner is private for the patient
The system SHALL send a patient or companion turn's manner and emotion to the physician's controller only.

#### Scenario: Controller sees it
- **WHEN** a patient turn settles
- **THEN** the controller receives its manner and emotion and no shared or patient screen receives either
