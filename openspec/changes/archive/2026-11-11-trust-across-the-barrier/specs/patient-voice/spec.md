# Spec Delta

## Purpose

Gives the patient their own controls during the visit, in their own language, so they can say they did not understand, ask for slower or repeated speech, pause, or ask for a human interpreter without needing the physician's permission or the physician's language.

## ADDED Requirements

### Requirement: Patient device
The system SHALL provide a patient device screen that, once consent is given, shows the latest spoken translation in the patient's language and five controls with the patient's language first and English beneath: I did not understand, please slow down, say that again, pause, and a human interpreter.

#### Scenario: Controls appear after consent
- **WHEN** the patient gives consent on their device
- **THEN** the five controls appear in the patient's language with English beneath, each at least 56 pixels tall

#### Scenario: Before consent
- **WHEN** the patient device is open and consent has not been given
- **THEN** only the consent notice and its button are shown

### Requirement: Signal reaches everyone
The system SHALL, when the patient sends a signal, show it on the shared screen in both languages, show it on the physician's controller, and record it in the visit record after the most recent turn.

#### Scenario: I did not understand
- **WHEN** the patient taps "I did not understand" after the physician's third turn
- **THEN** the shared screen shows, in the patient's language and in English, that the patient did not understand and asks the physician to say it another way, the controller lists the signal, and the record holds a signal entry after the third turn

### Requirement: Signal spoken to the physician
The system SHALL, for "I did not understand" and "please slow down", have the interpreter say a fixed line to the physician in the physician's language, naming the patient when known, through the same speak gate as every other line.

#### Scenario: Interpreter relays the signal
- **WHEN** the patient Mr Singh taps "please slow down"
- **THEN** the interpreter says, in English, that Mr Singh is asking the doctor to speak more slowly, and nothing is spoken in the patient's language

### Requirement: Say that again
The system SHALL, on "say that again", replay the most recent spoken translation in the patient's language without translating again, and SHALL refuse the request when nothing has yet been spoken in the patient's language.

#### Scenario: Replay
- **WHEN** the patient taps "say that again" after a physician turn was spoken in Punjabi
- **THEN** the same Punjabi audio is played again and no new turn is created

#### Scenario: Nothing to replay
- **WHEN** the patient taps "say that again" before any translation has been spoken
- **THEN** the device shows, in the patient's language, that there is nothing to repeat yet

### Requirement: Pause and interpreter from the patient
The system SHALL let the patient pause and resume capture and request a human interpreter from their own device, with the same effect as the existing controls.

#### Scenario: Patient pauses
- **WHEN** the patient taps pause on their device
- **THEN** the shared screen shows the paused notice in both languages, no turn is captured until resumed, and the patient's device shows resume

### Requirement: Signals are held, not spammed
The system SHALL accept at most one signal every two seconds from the same device, and SHALL refuse signals before consent and while paused.

#### Scenario: Double tap
- **WHEN** the patient taps a signal twice within two seconds
- **THEN** the second tap is refused and the device shows a short wait notice

### Requirement: Patient emotion never on the patient's device
The system SHALL NOT show any emotion, manner, certainty, back-translation, nudge, or trust information on the patient's device.

#### Scenario: Worried patient
- **WHEN** a patient turn is analysed as worried
- **THEN** the patient's device shows the turn's text only
