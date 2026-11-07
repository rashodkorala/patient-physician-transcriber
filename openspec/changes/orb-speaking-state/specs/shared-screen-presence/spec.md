# Spec Delta

## Purpose

Defines how the shared screen shows what the interpreter is doing right now, so both people in the room can tell whose turn it is without reading.

## ADDED Requirements

### Requirement: The screen shows when the interpreter is speaking
The shared screen SHALL show a Speaking state while the interpreter's voice is playing in the room, for relayed turns and for the interpreter's own lines, and SHALL leave it when the voice stops.

#### Scenario: Relay spoken
- **WHEN** a turn passes its checks and its relay starts playing
- **THEN** the shared screen shows Speaking until the relay finishes

#### Scenario: Interpreter's own line
- **WHEN** the interpreter speaks its introduction or asks for a name
- **THEN** the shared screen shows Speaking while that line plays

### Requirement: Speaking is shown only for words that may be spoken
The shared screen SHALL NOT show Speaking for a turn that is blocked, escalated, rejected, or not yet settled, whatever any client reports.

#### Scenario: Blocked turn reported as playing
- **WHEN** a client reports playback for a blocked turn
- **THEN** the shared screen does not show Speaking

### Requirement: Speaking never sticks
The shared screen SHALL leave the Speaking state when the device playing the voice disconnects, and within 60 seconds when the end of playback is never reported.

#### Scenario: Laptop drops off mid-relay
- **WHEN** the physician's laptop disconnects while a relay is playing
- **THEN** the shared screen leaves Speaking at once

#### Scenario: Lost end of playback
- **WHEN** playback starts and its end is never reported
- **THEN** the shared screen leaves Speaking within 60 seconds

### Requirement: A screen that joins mid-speech is current
A shared screen that opens or reconnects while the interpreter is speaking SHALL show Speaking straight away.

#### Scenario: TV reconnects during a relay
- **WHEN** the TV reconnects while a relay is playing
- **THEN** it shows Speaking without waiting for the next relay
