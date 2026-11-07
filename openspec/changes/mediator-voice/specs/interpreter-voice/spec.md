# Spec Delta

## Purpose

Defines when the interpreter's words are spoken aloud and how they sound: a natural, expressive voice that follows the speaker's tone, and never speaks anything that has not passed its checks.

## ADDED Requirements

### Requirement: Only checked words are spoken
The system SHALL speak only a turn whose outcome is final, a read-back turn after the physician confirms it, or one of the interpreter's own introduction lines. A blocked, escalated, rejected, or unsettled turn SHALL never be spoken, whichever screen asks.

#### Scenario: Blocked turn
- **WHEN** a turn is blocked for a critical value mismatch
- **THEN** no audio is produced for it, even if a client requests it

#### Scenario: Read-back confirmed
- **WHEN** the physician confirms the read-back of a dose
- **THEN** the relay is spoken, and not before

### Requirement: Delivery follows the speaker's tone
The system SHALL speak each relay in a natural human voice whose delivery matches the speaker's emotion and certainty: calm and gentle for worrying news, warm for reassurance, clear and steady for instructions.

#### Scenario: Worried patient
- **WHEN** the patient's turn is read as worried
- **THEN** the relay to the physician is spoken in a calm, serious voice, not a cheerful one

#### Scenario: Reassurance
- **WHEN** the physician reassures the patient
- **THEN** the relay is spoken warmly

### Requirement: Voices for every visit language
The system SHALL speak in each supported visit language with one consistent interpreter voice per visit, and SHALL fall back to the previous voice provider for a language if the new voice is unavailable, without dropping the turn.

#### Scenario: Provider unavailable
- **WHEN** the voice service fails for a final turn
- **THEN** the turn is spoken by the fallback voice and the failure is logged

### Requirement: Speech starts promptly
The system SHALL start speaking a relay quickly enough that the per-turn latency target from the demo-night build is still met, and SHALL log speech start time per turn.

#### Scenario: Latency measured
- **WHEN** a final turn is spoken
- **THEN** the latency log records when audio started, separately from recognition and server time
