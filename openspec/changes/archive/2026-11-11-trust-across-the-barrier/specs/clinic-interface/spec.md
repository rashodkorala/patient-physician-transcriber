# Spec Delta

## Purpose

Makes every screen read as one clinic tool: light, legible from a tablet at arm's length and a TV at three metres, accessible, and calm.

## ADDED Requirements

### Requirement: One design system on every screen
The system SHALL style every screen from one shared set of design tokens, light by default, honouring the device's dark preference.

#### Scenario: Dark preference
- **WHEN** a device prefers a dark colour scheme
- **THEN** every screen, including the shared screen, uses the dark token set with the same meanings

### Requirement: Legible captions
The system SHALL show captions on the shared screen at a size readable from three metres on a 40 inch display, with the original and the translation side by side and the physician's manner label beneath the translation.

#### Scenario: 1080p display
- **WHEN** the shared screen is shown at 1920 by 1080 pixels
- **THEN** caption text is at least 32 pixels tall and both columns fit without horizontal scrolling

### Requirement: Colour carries meaning only
The system SHALL use colour only to tell apart the physician, the patient, the companion, and the states verified, waiting, and stop, and SHALL always pair colour with a label or a shape.

#### Scenario: Blocked turn
- **WHEN** a turn is blocked
- **THEN** it is shown with the stop colour and the words "not spoken"

### Requirement: Accessible targets and focus
The system SHALL make every control on the patient's device at least 56 pixels tall and every other control at least 44 pixels, and SHALL show a visible focus ring on keyboard focus.

#### Scenario: Patient device on a phone
- **WHEN** the patient device is shown at 390 pixels wide
- **THEN** every signal control fills the width, is at least 56 pixels tall, and the page does not scroll horizontally

### Requirement: Reduced motion respected
The system SHALL stop every non-essential animation when the device asks for reduced motion.

#### Scenario: Reduced motion
- **WHEN** reduced motion is preferred
- **THEN** the orb and the speaking rings do not animate and every state is still told apart

### Requirement: Sentence case and plain words
The system SHALL write every label in sentence case in plain words, naming what a control does, and SHALL show the patient's language before English on the patient's device.

#### Scenario: Patient device labels
- **WHEN** the patient's language is Tamil
- **THEN** every label on the patient's device is in Tamil with English beneath it
