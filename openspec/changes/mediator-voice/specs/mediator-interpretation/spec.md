# Spec Delta

## Purpose

Defines how the interpreter relays each turn as a person standing between the physician and the patient, in reported speech that names the speaker, while keeping every clinical detail exact.

## ADDED Requirements

### Requirement: Reported speech naming the speaker
The system SHALL relay every turn in the listener's language as reported speech that names the speaker, in both directions. Without a known name it SHALL use "your doctor" for the physician, "the patient" for the patient, and "the patient's companion" for a companion.

#### Scenario: Physician turn with a known name
- **WHEN** the physician's name is Dr. Thomas and the physician says "You need to take this medicine two times a day after every meal"
- **THEN** the patient hears and sees, in their language, a sentence meaning "Dr. Thomas is saying you should take this medicine 2 times a day after every meal"

#### Scenario: Patient turn with a known name
- **WHEN** the patient's name is Harpreet and the patient says, in Punjabi, that their chest has hurt since Monday
- **THEN** the physician hears and sees a sentence meaning "Harpreet is saying their chest has hurt since Monday"

#### Scenario: No names known
- **WHEN** no names are set and the physician gives an instruction
- **THEN** the patient hears it framed as "Your doctor is saying ..."

### Requirement: Meaning kept exactly
The system SHALL keep every instruction, number, dose, unit, frequency, date, and medication name exactly. It MAY use plain everyday wording, and SHALL NOT soften, strengthen, add, or drop any instruction, warning, or question.

#### Scenario: Critical values unchanged by the frame
- **WHEN** a physician turn contains "500 mg" and "twice a day"
- **THEN** the reported-speech translation contains the same dose and frequency, and the critical value check passes as it would for a direct translation

#### Scenario: Warning kept
- **WHEN** the physician says "Stop the medicine at once if you get a rash"
- **THEN** the relayed sentence keeps both the condition and the instruction to stop at once

### Requirement: Emotion and certainty carried into the relay
The system SHALL keep the speaker's emotion and level of certainty in the relayed sentence, and SHALL add warmth only in the reporting frame, never in a way that changes how serious or certain the news is.

#### Scenario: Uncertain news stays uncertain
- **WHEN** the physician says "It might be an infection, we need a test to be sure"
- **THEN** the relay keeps that it might be an infection and that a test is needed, without sounding certain

### Requirement: Relay only, no own advice
The system SHALL relay only what the speaker said. It SHALL NOT answer a question on someone's behalf or add medical advice of its own.

#### Scenario: Patient asks a question
- **WHEN** the patient asks "Can I take it with food?"
- **THEN** the physician hears the question relayed, for example "Harpreet is asking whether they can take it with food", and the interpreter gives no answer itself

### Requirement: Reporting frame does not fail the tone check
The system SHALL treat the reporting frame and the switch from first to third person as expected when checking tone, and SHALL still fail a turn whose meaning, certainty, or warmth changed.

#### Scenario: Frame alone passes
- **WHEN** a relay adds only "Dr. Thomas is saying" to an otherwise faithful translation
- **THEN** the tone check passes and the turn is not escalated

#### Scenario: Softened news fails
- **WHEN** a relay turns "this is serious" into "this is nothing to worry about"
- **THEN** the tone check fails and the turn is retried, then escalated as today
