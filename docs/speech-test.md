# Speech Test Log (demo-night-mvp tasks 1.3 and 1.4)

Record every speech check on the demo laptop. ADR-005: switch to Google Speech if Punjabi fails.

## Task 1.3: round trip per language

| Date | Language | Recognised correctly? | Voice natural? | Notes |
|---|---|---|---|---|
| | pa-IN (Punjabi) | | | |
| | fr-CA (French) | | | |
| | en-CA (English) | | | |

## English push-to-talk smoke test

On 17 November 2026, Chrome fed a synthetic English sentence through its microphone input to Azure Speech using the app's `/control` push-to-talk button.
The speech-token endpoint returned 200 and the recognised sentence appeared as the English original on `/screen`.
The fixture looped while the button was held, so the caption contained repeated copies of the sentence.
This run used the fake translator and did not check a physical microphone, Punjabi or French recognition, translation accuracy, or spoken playback.

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

## Continuous-listening task 2.1: language identification for hands-free

Run on 2026-11-07 with synthesised speech, not a live speaker: Azure voices spoke each line, and the audio was fed to Azure recognition.
The live run with the speakers stays open until native-speaker testing starts.
Continuous language identification compared English (`en-CA`) with each patient language.

| Pair | Full sentences | One-word reply | Notes |
|---|---|---|---|
| `en-CA` alone vs each patient language | English every time | "Yes." heard as English | |
| `en-CA` / `pa-IN` | Punjabi, both sentences | "ਹਾਂ ਜੀ।" heard as Punjabi | |
| `en-CA` / `fr-CA` | French, both sentences | "Oui." heard as English "We." | |
| `en-CA` / `ta-IN` (Tamil) | Tamil, both sentences | "ஆமாம்." heard as English "Ah, Mum." | `ta-LK` is refused for recognition (websocket code 1007), so Tamil is identified and recognised as `ta-IN` |
| `en-CA` / `si-LK` | Sinhala, both sentences | "ඔව්." heard as English "Oh." | |

Azure reports no confidence for continuous identification: every result said "Unknown".

**Outcome:** language identification separates the two sides on full sentences in every pair.
One- and two-word replies are often heard as English, so hands-free holds them on the controller for a Physician or Patient tap before sending (rashodkorala's decision, 2026-11-07).
Tamil recognition had the same `ta-LK` problem in push-to-talk, fixed by recognising Tamil as `ta-IN` (commit 2b9bd7f).
