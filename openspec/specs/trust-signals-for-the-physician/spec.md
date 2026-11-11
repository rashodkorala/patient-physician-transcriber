# trust-signals-for-the-physician Specification

## Purpose
Shows the physician, privately and during the visit, how the conversation is landing: the patient's emotion over time, whether a reassurance landed, every patient signal, and a cultural cue when a topic is sensitive in the patient's culture.

## Requirements

### Requirement: Private trust view
The system SHALL show on the physician's controller, and only there, a trust view with one entry per spoken turn and per patient signal.

#### Scenario: Shared screen receives nothing
- **WHEN** a trust entry is produced
- **THEN** the controller shows it and no shared or patient screen receives it, live or when it connects later

### Requirement: Emotion over time
The system SHALL show, for each spoken patient or companion turn, the emotion read from it, in order, so the physician can see how the patient's state changed through the visit.

#### Scenario: Worry then relief
- **WHEN** the patient sounds worried in one turn and relieved two turns later
- **THEN** the trust view shows worried, then relieved, in order

### Requirement: Reassurance landed
The system SHALL mark a patient turn as reassurance landed when the patient sounded worried, embarrassed, in pain, or confused earlier, the physician then spoke with a reassuring, warm, gentle, or encouraging manner, and the patient now sounds calm or relieved; and SHALL mark it as not yet landed when the patient still sounds worried after such a physician turn.

#### Scenario: Landed
- **WHEN** a worried patient turn is followed by a reassuring physician turn and then a calm patient turn
- **THEN** the calm turn is marked as reassurance landed

#### Scenario: Not yet
- **WHEN** a worried patient turn is followed by a reassuring physician turn and then another worried patient turn
- **THEN** the second worried turn is marked as not yet landed

#### Scenario: No earlier worry
- **WHEN** a calm patient turn follows a reassuring physician turn with no earlier worry
- **THEN** the turn carries no landed mark

### Requirement: Patient signals listed
The system SHALL list every patient signal in the trust view, with the turn it followed, and SHALL suggest to the physician how to respond to it.

#### Scenario: Not understood
- **WHEN** the patient signals they did not understand
- **THEN** the trust view lists the signal after the turn it followed with a suggestion to say it another way, in shorter sentences

### Requirement: Culture cue
The system SHALL show the physician a short cue when a physician turn touches a topic the patient language's tone and culture guide marks as sensitive, and SHALL show nothing when it does not.

#### Scenario: Sensitive question
- **WHEN** the physician asks a Punjabi patient about alcohol
- **THEN** the trust view shows a cue that the question may carry shame in the patient's culture and suggests saying why it matters for care

#### Scenario: Everyday question
- **WHEN** the physician asks how long the symptoms have lasted
- **THEN** no cue is shown

### Requirement: Cues stay out of the record
The system SHALL NOT include any trust entry, cue, or landed mark in the clinical note, the patient summary, or the record chain.

#### Scenario: Note generated after cues
- **WHEN** the note is generated after several cues were shown
- **THEN** the note contains no cue text and the chain holds no trust entry
