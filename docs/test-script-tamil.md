# Test Script: Tamil (before demo night)

> **Status: DRAFT test script. Not for the stage.**
> - Purpose: run every demo beat in Tamil before 19 November 2026 to see how recognition, translation, tone, safety checks, and latency hold up in a lower-resource language.
> - Needs TDM-003 (proposed): Tamil is selectable only in test mode. Until TDM-003 is accepted, this script can be rehearsed on paper but not run in the app.
> - Every Tamil line is Claude's draft. The Tamil speaker must rewrite each one in the words they would naturally say, then sign off.
> - A clinician must check the medical content. Patient and doctor are fictional. Nothing here is medical advice.
> - Uses TDM-002 (presenter mismatch control) in step 7.

## At a glance

| Item | Detail |
|---|---|
| Condition | New type 2 diabetes |
| Plan | Metformin 500 mg twice a day with meals; HbA1c blood test in 3 months; walk 30 minutes a day |
| Patient | Mrs Meena Rajaratnam, 54, Scarborough (Sri Lankan Tamil) |
| Physician | Dr Patel (English) |
| Length | About 6 minutes |
| Cast | Tester or narrator, physician, Tamil speaker as patient |

## Set-up

- Laptop with test mode enabled (TDM-003); `/control` on the laptop, `/screen` on a TV or second monitor, `/review` on a phone.
- Microphones as for the demo; presenter mode on (mismatch and tamper controls).
- Open the test log at the end of this file before starting.

## Steps

### 1. Language picker (Requirement: Language selection)

- **Physician:** turns on test mode, then selects தமிழ் (Tamil).
- **Check:** Tamil is selectable only because test mode is on; with test mode off it shows "coming soon".

### 2. Consent (Requirement: Consent in the patient's language)

- **Patient:** reads the Tamil consent notice and taps consent.
- **Check:** the notice is in Tamil script and reads naturally to the speaker.

### 3. Symptoms (Requirements: Push-to-talk turns, Bilingual captions, Translation is spoken aloud, Tone-preserving translation, Tone labels)

| # | Speaker | Line (English meaning) | Draft line for the Tamil speaker |
|---|---|---|---|
| 3.1 | Physician | "Hello Mrs Rajaratnam, I'm Dr Patel. This screen shows what we both say, in Tamil and in English. What brings you in today?" | (English, final) |
| 3.2 | Patient | "Hello doctor. For a few months I have been very thirsty, I get up many times at night to pass urine, and I am always tired." | வணக்கம் டாக்டர். கடந்த சில மாதங்களாக எனக்கு அடிக்கடி தாகமாக இருக்கிறது. இரவில் பல முறை சிறுநீர் கழிக்க எழுகிறேன். எப்போதும் களைப்பாக இருக்கிறது. |
| 3.3 | Patient | "I am 54. My mother had sugar disease." | எனக்கு ஐம்பத்து நான்கு வயது. என் அம்மாவுக்கு சர்க்கரை வியாதி இருந்தது. |

- **Check:** respectful register in Tamil for the physician's lines; "sugar disease" (a common lay term) maps to diabetes; one translation-register label on each spoken caption.
- **Keep for step 9:** if "54" (ஐம்பத்து நான்கு) is heard as "45" (நாற்பத்து ஐந்து), leave it for transcript review.

### 4. Mark high risk before the diagnosis (Requirement: Human interpreter offer)

| # | Speaker | Line | Check |
|---|---|---|---|
| 4.1 | Physician | presses "mark high risk" (a serious new diagnosis) | Interpreter offer in Tamil and English; simulated connection closes with "Interpreter would join here (simulated)" |
| 4.2 | Physician | "Your blood tests show that you have type 2 diabetes. It is common, and it is very manageable." | Tone label "reassuring"; certainty preserved; no extra alarm in the back-translation |

### 5. Empathy (Requirements: Empathy nudge, Patient emotion stays with the physician)

| # | Speaker | Line (English meaning) | Draft line for the Tamil speaker |
|---|---|---|---|
| 5.1 | Patient | "Doctor, will I need injections? I am very afraid of needles." | டாக்டர், எனக்கு ஊசி போட வேண்டுமா? எனக்கு ஊசி என்றால் மிகவும் பயம். |
| 5.2 | Physician (nudge phrase) | "Many people worry about that. Right now you do not need injections. We will start with tablets." | (English, final) |

- **Check:** the controller shows a private nudge about the fear of needles; the TV shows no emotion.

### 6. Off-the-record pause and disclosure (Requirement: Off-the-record pause)

| # | Speaker | Line (English meaning) | Draft line for the Tamil speaker |
|---|---|---|---|
| 6.1 | Patient | "Who will see what I say here?" | நான் இங்கே சொல்வதை யார் பார்ப்பார்கள்? |
| 6.2 | Physician | "Only you, me, and your care team. You can pause the recording at any time with that button." | (English, final) |
| 6.3 | Patient | presses pause, waits, presses resume | (no speech) |
| 6.4 | Patient | "On fasting days I eat nothing until the evening. I was hesitant to tell you." | விரதம் இருக்கும் நாட்களில் மாலை வரை நான் எதுவும் சாப்பிடுவதில்லை. அதை உங்களிடம் சொல்லத் தயங்கினேன். |
| 6.5 | Physician | "Thank you for telling me. Take the tablet with the meal when you break your fast, never on an empty stomach. We will plan around your fasting days." | (English, final) |

- **Check:** the paused notice in Tamil and English; nothing captured during the pause; "fasting" (விரதம்) translated with its religious sense, not as dieting.

### 7. Blocked dose, then read-back (Requirements: Presenter mismatch control, Critical value mismatch blocks speech, Turn outcome precedence, Critical value read-back)

| # | Speaker | Line | Expected outcome |
|---|---|---|---|
| 7.1 | Presenter | arms the mismatch control | Controller shows "armed" |
| 7.2 | Physician | "Take metformin, 500 milligrams, twice a day with meals." | Injection makes it 5000 mg; **blocked**; nothing spoken; TV shows the original and a repeat notice |
| 7.3 | Physician | repeats 7.2 | Values match; read-back of 500 mg, twice a day, with meals; confirm; spoken |
| 7.4 | Physician | "We will check a blood test called HbA1c in 3 months." | Read-back on 3 months; confirm; spoken |
| 7.5 | Physician | "Try to walk for 30 minutes every day." | Read-back on 30 minutes; confirm; spoken |

- **Check:** Tamil numerals or words for 500 and 3 match; "with meals" survives translation; "HbA1c" is explained in plain Tamil from the glossary.

### 8. Explain-back (Requirement: Explain-back check)

| # | Speaker | Line (English meaning) | Draft line for the Tamil speaker |
|---|---|---|---|
| 8.1 | Physician | "To make sure I explained it well, can you tell me in your own words how you will take the tablets?" | (English, final) |
| 8.2 | Patient | "One tablet in the morning and one at night. Walk every day." (leaves out "with meals") | காலையில் ஒரு மாத்திரை, இரவில் ஒரு மாத்திரை. தினமும் நடக்க வேண்டும். |
| 8.3 | Physician | "And always take the tablet with food." | (English, final) |
| 8.4 | Patient | "I take the tablet with my meal." | சாப்பாட்டுடன் மாத்திரை எடுக்க வேண்டும். |

- **Check:** after 8.2, "with meals" is marked missed; after 8.4, all matched.

### 9. Transcript review (Requirement: Transcript review)

| # | Speaker | Line (English meaning) | Draft line for the Tamil speaker |
|---|---|---|---|
| 9.1 | Patient | "I said fifty-four, not forty-five." (only if 3.3 was misheard) | நான் ஐம்பத்து நான்கு என்று சொன்னேன், நாற்பத்து ஐந்து அல்ல. |

- **Check:** the corrected turn and its new translation; the history keeps the original. If everything was heard correctly, the patient confirms 3.3 instead.

### 10. Note, summary, and record verified (Requirements: Note with provenance tags, Patient summary, Record verified badge)

- **Check:**
  - "Thirst and night-time urination for months" is tagged patient-stated and links to 3.2.
  - "Type 2 diabetes" is tagged physician-stated (4.2).
  - Any assessment the model adds is tagged AI inference.
  - The Tamil summary reads aloud with 500 mg, twice a day, with meals, 3 months, and 30 minutes exactly as confirmed.
  - The badge is green; the tamper control turns it red and names the altered turn.

## Test log

Fill in one row per step on each test run.

| Run date | Step | Recognition (heard correctly? errors) | Latency (s) | Outcome (final, read-back, blocked, escalated) | Tone: accuracy / respect / warmth (1 to 5) | Issues |
|---|---|---|---|---|---|---|
| | 3 | | | | | |
| | 4 | | | | | |
| | 5 | | | | | |
| | 6 | | | | | |
| | 7 | | | | | |
| | 8 | | | | | |
| | 9 | | | | | |
| | 10 | | | | | |

**Run summary:** median latency; number of retries, blocks, and escalations; glossary gaps found; lines the speaker found unnatural or disrespectful; verdict (ready, needs work, not safe). Copy the summary into `docs/language-benchmark.md`.

## Sign-off

| Role | Name | Checked | Date |
|---|---|---|---|
| Tamil speaker (all Tamil lines rewritten and approved) | | [ ] | |
| Clinician (type 2 diabetes explanation, metformin 500 mg twice a day with meals, fasting advice, HbA1c in 3 months) | | [ ] | |
| Project lead (rashodkorala) | | [ ] | |
