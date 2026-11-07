# Spec Delta

## Purpose

Defines how the interpreter opens a visit as a real interpreter would: introducing itself to both people, learning their names, and skipping what is already known so the visit starts quickly.

## ADDED Requirements

### Requirement: Spoken introduction
The system SHALL let the physician start an introduction before the first turn. The interpreter SHALL introduce itself in the physician's language and in the patient's language, both spoken and shown on the shared screen.

#### Scenario: Introduction at the start
- **WHEN** the physician starts the introduction in a new Punjabi visit
- **THEN** the interpreter says, in English and in Punjabi, that it will interpret between them for this visit

#### Scenario: Introduction after a turn
- **WHEN** the visit already has a turn
- **THEN** the system does not offer the introduction

### Requirement: Asking for names in order
During the introduction the interpreter SHALL ask for the physician's name in the physician's language, then the patient's name in the patient's language, skipping any name already known.

#### Scenario: Both names unknown
- **WHEN** neither name is known
- **THEN** the interpreter asks the physician first, then the patient

#### Scenario: Physician name already saved
- **WHEN** a default physician name is saved on the device
- **THEN** the interpreter greets the patient on the physician's behalf by that name and asks only for the patient's name

### Requirement: Names confirmed before use
The system SHALL show a name heard in a spoken reply to the physician for confirmation, and SHALL use it only once confirmed. The physician SHALL be able to correct it by typing or ask the interpreter to ask again.

#### Scenario: Name confirmed
- **WHEN** the physician replies "Doctor Thomas" and confirms the proposed name "Dr. Thomas"
- **THEN** later relays name "Dr. Thomas"

#### Scenario: Name misheard
- **WHEN** the proposed name is wrong and the physician rejects it
- **THEN** the interpreter asks again, and the physician can type the name instead

### Requirement: Saved default physician name
The system SHALL let a physician or clinic save a default physician name on the device, applied to every new visit on it until changed or cleared. The physician SHALL be able to change names during a visit.

#### Scenario: Default applied
- **WHEN** "Dr. Thomas" is saved as the default and a new visit starts
- **THEN** the visit's physician name is "Dr. Thomas" without asking

#### Scenario: Name changed mid-visit
- **WHEN** the physician changes the patient's name during the visit
- **THEN** turns from then on use the new name and earlier turns are unchanged

### Requirement: Introduction is optional
The system SHALL let the physician skip the introduction, and SHALL never require names before a turn.

#### Scenario: Skipped
- **WHEN** the physician skips the introduction and the first turn is spoken
- **THEN** the turn is relayed with "your doctor" or "the patient" as needed
