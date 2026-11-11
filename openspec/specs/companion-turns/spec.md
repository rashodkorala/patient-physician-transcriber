# companion-turns Specification

## Purpose
Lets a family member or friend who came with the patient speak in the patient's language as a labelled third speaker, so their words are relayed and recorded as theirs and never confused with the patient's.

## Requirements

### Requirement: Companion speaker control
The system SHALL provide a companion speaker control on the physician's controller that captures a turn in the patient's language with speaker companion.

#### Scenario: Companion speaks
- **WHEN** the physician holds the companion control and the companion speaks Punjabi
- **THEN** the turn is recorded with speaker companion and language Punjabi, and the physician hears it relayed as what the patient's companion is saying

#### Scenario: Wrong language refused
- **WHEN** a companion turn is submitted in the physician's language
- **THEN** the turn is refused and the controller explains that a companion speaks the patient's language

### Requirement: Companion labelled everywhere
The system SHALL label a companion turn as companion on the shared screen, the patient's device, the controller, the record view, and the note's provenance tag.

#### Scenario: Caption and note
- **WHEN** a companion turn is spoken and the note is later generated
- **THEN** the caption carries the companion label and any note sentence drawn only from that turn is tagged companion-stated

### Requirement: Companion turns do not nudge
The system SHALL NOT produce an empathy nudge or a reassurance-landed mark from a companion turn.

#### Scenario: Worried companion
- **WHEN** a companion turn sounds worried
- **THEN** the controller shows the emotion in the trust view but no nudge is produced

### Requirement: Hands-free never labels a companion
The system SHALL route hands-free turns in the patient's language to the patient, and SHALL rely on the companion control for a companion.

#### Scenario: Companion while hands-free
- **WHEN** hands-free listening is on and the companion speaks
- **THEN** the turn is labelled patient unless the physician used the companion control
