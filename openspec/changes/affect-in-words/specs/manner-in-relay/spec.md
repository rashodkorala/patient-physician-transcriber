# Spec Delta

## Purpose

Carries how the physician said something, not only what, so the patient hears and reads the care in the physician's words; and conveys the patient's affect to the physician in words, through one hedged phrase in the reporting frame, without exposing it as a label to the room or to the patient.
The interpreter's voice stays the same for every turn and every interpreter line.

## MODIFIED Requirements

### Requirement: Manner in the interpreter's voice
The system SHALL speak every turn, physician, patient, and companion, and every interpreter line (introduction, name question, or signal line), in one constant voice delivery that does not vary by manner, emotion, certainty, or kind of line.
The system SHALL express a patient or companion turn's affect in words: when the speaker's affect is clearly not plain, the spoken relay to the physician SHALL carry exactly one hedged affect phrase inside the reporting frame only, and a plain turn SHALL carry none.
A physician turn SHALL keep the existing reporting-frame adverb rule and SHALL carry no affect phrase.

#### Scenario: Urgent instruction
- **WHEN** a physician turn with manner urgent is spoken
- **THEN** the voice delivery is the same as for any other turn, and the urgency appears only as the existing frame adverb when the words alone would lose it

#### Scenario: Interpreter line
- **WHEN** the interpreter speaks an introduction, a name question, or a signal line
- **THEN** it is spoken in the same constant delivery as a turn relay, with no separate warm delivery

#### Scenario: Worried patient conveyed
- **WHEN** a worried patient turn is relayed to the physician
- **THEN** the relay opens with a frame such as "The patient says, sounding worried, ...", the voice delivery is the constant one, and there is exactly one affect phrase

#### Scenario: Companion turn
- **WHEN** a companion's turn whose affect is clearly embarrassed is relayed to the physician
- **THEN** the frame names the companion and carries one hedged phrase such as "sounding embarrassed"

#### Scenario: Plain patient turn
- **WHEN** a patient turn without marked feeling is relayed to the physician
- **THEN** the frame carries no affect phrase

#### Scenario: Neutral words in a worried voice
- **WHEN** a patient says neutral words in a worried voice
- **THEN** the turn is read from the words alone, so it is read as plain and carries no affect phrase

### Requirement: Manner never changes meaning
The system SHALL keep every instruction, certainty, and critical value unchanged whatever the manner or affect, a manner word or affect phrase MAY appear only once per relay, and only inside the reporting frame.

#### Scenario: Dose with a gentle manner
- **WHEN** the physician gently gives a dose of 0.4 milligrams
- **THEN** the relay keeps 0.4 milligrams, the critical value check passes as before, and any manner word sits only in the opening frame

#### Scenario: Frame adverb accepted by the tone check
- **WHEN** a relay adds only "gently" to the reporting frame of an otherwise faithful translation
- **THEN** the tone check passes and the turn is not escalated

#### Scenario: Frame phrase accepted by the tone check
- **WHEN** a patient relay adds only "sounding worried" to the reporting frame of an otherwise faithful translation
- **THEN** the tone check passes and the turn is not escalated

#### Scenario: Patient states a value with an affect phrase
- **WHEN** a worried patient says they take 0.4 milligrams
- **THEN** the relay keeps 0.4 milligrams, the critical value check passes as before, and the affect phrase sits only in the opening frame

#### Scenario: Phrase that changes meaning
- **WHEN** a relay's affect phrase makes the patient's statement sound more or less certain or serious than it was said
- **THEN** the tone check fails the relay as it would for any change of certainty

### Requirement: Manner is private for the patient
The system SHALL send a patient or companion turn's manner and emotion to the physician's controller as a label only, and SHALL show no manner or emotion label on any shared screen or on the patient's device.
The only other place the patient's affect appears is the single hedged phrase in the reporting frame of the relay, which is spoken aloud in the room in the physician's language and is part of the translation text.

#### Scenario: Controller sees it
- **WHEN** a patient turn settles
- **THEN** the controller receives its manner and emotion as a label, and no shared or patient screen receives a manner or emotion label

#### Scenario: The phrase is spoken in the room
- **WHEN** a worried patient's relay is spoken to the physician
- **THEN** the affect phrase is heard in the physician's language, as part of the relay, and no separate label is shown on any shared or patient screen
