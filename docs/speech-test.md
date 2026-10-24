# Speech Test Log (demo-night-mvp tasks 1.3 and 1.4)

Record every speech check on the demo laptop. ADR-005: switch to Google Speech if Punjabi fails.

## Task 1.3: round trip per language

| Date | Language | Recognised correctly? | Voice natural? | Notes |
|---|---|---|---|---|
| | pa-IN (Punjabi) | | | |
| | fr-CA (French) | | | |
| | en-CA (English) | | | |

## Task 1.4: Punjabi accuracy with the speaker

Use the patient lines from `docs/demo-script.md` (Run 1), spoken naturally by the Punjabi speaker, three times each.

| Line | Attempt | Heard as | Word errors | Numbers right? | Notes |
|---|---|---|---|---|---|
| 3.2 | 1 | | | | |
| 3.4 | 1 | | | | |
| 4.1 | 1 | | | | |
| 4.4 | 1 | | | | |
| 7.2 | 1 | | | | |
| 7.4 | 1 | | | | |
| 8.1 | 1 | | | | |

**Decision rule (ADR-005):** if numbers are misheard in more than one line, or more than one word in five is wrong overall, repeat with Google Speech and record both. The project lead decides which provider to keep.

**Verdict:**
