# Test Script: Sinhala (before demo night)

> **Status: DRAFT test script. Not for the stage.**
> - Purpose: run every demo beat in Sinhala before 19 November 2026 to see how recognition, translation, tone, safety checks, and latency hold up in what is expected to be the weakest of our languages for medical content.
> - Needs TDM-003 (proposed): Sinhala is selectable only in test mode. Until TDM-003 is accepted, this script can be rehearsed on paper but not run in the app.
> - Every Sinhala line is Claude's draft. The Sinhala speaker must rewrite each one in the words they would naturally say, then sign off.
> - A clinician must check the medical content. Patient and doctor are fictional. Nothing here is medical advice.
> - Uses TDM-002 (presenter mismatch control) in step 7.

## At a glance

| Item | Detail |
|---|---|
| Condition | High blood pressure found at a pharmacy check, with occasional chest discomfort |
| Plan | Amlodipine 5 mg once a day; home blood pressure readings twice a day for 2 weeks; follow-up visit in 4 weeks; urgent ECG referral for the chest discomfort |
| Patient | Mr Nimal Perera, 63, Mississauga |
| Physician | Dr Patel (English) |
| Length | About 6 minutes |
| Cast | Tester or narrator, physician, Sinhala speaker as patient |

## Set-up

- Laptop with test mode enabled (TDM-003); `/control` on the laptop, `/screen` on a TV or second monitor, `/review` on a phone.
- Microphones as for the demo; presenter mode on (mismatch and tamper controls).
- Before the first run, confirm that speech recognition and a natural Sinhala voice work at all (task 6.2). If not, record it in the test log and stop.
- Open the test log at the end of this file before starting.

## Steps

### 1. Language picker (Requirement: Language selection)

- **Physician:** turns on test mode, then selects සිංහල (Sinhala).
- **Check:** Sinhala is selectable only because test mode is on; with test mode off it shows "coming soon".

### 2. Consent (Requirement: Consent in the patient's language)

- **Patient:** reads the Sinhala consent notice and taps consent.
- **Check:** the notice is in Sinhala script and reads naturally to the speaker.

### 3. Symptoms (Requirements: Push-to-talk turns, Bilingual captions, Translation is spoken aloud, Tone-preserving translation, Tone labels)

| # | Speaker | Line (English meaning) | Draft line for the Sinhala speaker |
|---|---|---|---|
| 3.1 | Physician | "Hello Mr Perera, I'm Dr Patel. This screen shows what we both say, in Sinhala and in English. What brings you in today?" | (English, final) |
| 3.2 | Patient | "Ayubowan, doctor. They measured my pressure at the pharmacy. They said it was about 160. Sometimes I get headaches." | ආයුබෝවන් දොස්තර මහත්තයා. ෆාමසියේදී මගේ ප්‍රෙෂර් එක මැන්නා. ඒක එකසිය හැටක් විතර කියලා කිව්වා. සමහර වෙලාවට ඔළුව රිදෙනවා. |

- **Check:** respectful register in Sinhala for the physician's lines (for example the polite form of "you"); "pressure" (ප්‍රෙෂර්, a common loan word) maps to blood pressure; one translation-register label on each spoken caption.
- **Keep for step 9:** if "160" (එකසිය හැට) is heard as "116" (එකසිය දහසය), leave it for transcript review.

### 4. Empathy (Requirements: Empathy nudge, Patient emotion stays with the physician)

| # | Speaker | Line (English meaning) | Draft line for the Sinhala speaker |
|---|---|---|---|
| 4.1 | Patient | "Will the medicine cost a lot? I don't have insurance." | බෙහෙත් වලට ගොඩක් සල්ලි යනවද? මට රක්ෂණයක් නැහැ. |
| 4.2 | Physician (nudge phrase) | "I understand cost is a real worry. This medicine is low cost, and we will look at programmes that can help." | (English, final) |

- **Check:** the controller shows a private nudge about cost; the TV shows no emotion.

### 5. Off-the-record pause and disclosure (Requirement: Off-the-record pause)

| # | Speaker | Line (English meaning) | Draft line for the Sinhala speaker |
|---|---|---|---|
| 5.1 | Patient | "Who will see what I say here?" | මම මෙතන කියන දේවල් කවුද බලන්නේ? |
| 5.2 | Physician | "Only you, me, and your care team. You can pause the recording at any time with that button." | (English, final) |
| 5.3 | Patient | presses pause, waits, presses resume | (no speech) |
| 5.4 | Patient | "An earlier tablet made my ankles swell, so I stopped taking it. I didn't tell anyone." | කලින් දුන්න පෙත්ත නිසා මගේ වළලුකර ඉදිමුණා. ඒ නිසා මම ඒක බොන එක නැවැත්තුවා. මම කාටවත් කිව්වේ නැහැ. |
| 5.5 | Physician | "Thank you for telling me. Ankle swelling can happen with blood pressure tablets. If it happens with the new one, tell me and we will change it." | (English, final) |

- **Check:** the paused notice in Sinhala and English; nothing captured during the pause; "ankles swell" translated as a symptom, not as an injury.

### 6. Chest discomfort and mark high risk (Requirement: Human interpreter offer)

| # | Speaker | Line (English meaning) | Draft line for the Sinhala speaker |
|---|---|---|---|
| 6.1 | Patient | "Sometimes I feel discomfort in my chest." | සමහර වෙලාවට පපුවේ අපහසුවක් දැනෙනවා. |
| 6.2 | Physician | presses "mark high risk", then: "Because of the chest discomfort, I want you to have a heart test called an ECG today. I'd like a qualified interpreter to help us with this conversation." | (English, final) |

- **Check:** interpreter offer in Sinhala and English; simulated connection closes with "Interpreter would join here (simulated)"; the urgency is kept without sounding alarming.

### 7. Blocked dose, then read-back (Requirements: Presenter mismatch control, Critical value mismatch blocks speech, Turn outcome precedence, Critical value read-back)

| # | Speaker | Line | Expected outcome |
|---|---|---|---|
| 7.1 | Presenter | arms the mismatch control | Controller shows "armed" |
| 7.2 | Physician | "Take amlodipine, 5 milligrams, once a day." | Injection makes it 50 mg; **blocked**; nothing spoken; TV shows the original and a repeat notice |
| 7.3 | Physician | repeats 7.2 | Values match; read-back of 5 mg, once a day; confirm; spoken |
| 7.4 | Physician | "Measure your blood pressure at home twice a day for 2 weeks." | Read-back on twice a day and 2 weeks; confirm; spoken |
| 7.5 | Physician | "Come back to see me in 4 weeks." | Read-back on 4 weeks; confirm; spoken |

- **Check:** Sinhala numbers for 5, 2, and 4 match; "once a day" and "twice a day" are not confused.

### 8. Explain-back (Requirement: Explain-back check)

| # | Speaker | Line (English meaning) | Draft line for the Sinhala speaker |
|---|---|---|---|
| 8.1 | Physician | "To make sure I explained it well, can you tell me in your own words what you will do?" | (English, final) |
| 8.2 | Patient | "I take one tablet a day. I come back in four weeks." (leaves out the home readings) | දවසකට එක පාරක් පෙත්ත බොන්න ඕනේ. සති හතරකින් ආයෙත් එන්න ඕනේ. |
| 8.3 | Physician | "And please measure your blood pressure at home twice a day for 2 weeks." | (English, final; read-back) |
| 8.4 | Patient | "I measure my pressure twice a day for two weeks." | සති දෙකක් දවසට දෙපාරක් ප්‍රෙෂර් එක මනින්න ඕනේ. |

- **Check:** after 8.2, the home readings are marked missed; after 8.4, all matched.

### 9. Transcript review (Requirement: Transcript review)

| # | Speaker | Line (English meaning) | Draft line for the Sinhala speaker |
|---|---|---|---|
| 9.1 | Patient | "I said one hundred and sixty, not one hundred and sixteen." (only if 3.2 was misheard) | මම කිව්වේ එකසිය හැට, එකසිය දහසය නෙවෙයි. |

- **Check:** the corrected turn and its new translation; the history keeps the original. If everything was heard correctly, the patient confirms 3.2 instead.

### 10. Note, summary, and record verified (Requirements: Note with provenance tags, Patient summary, Record verified badge)

- **Check:**
  - "Pharmacy blood pressure about 160 with headaches" is tagged patient-stated and links to 3.2.
  - "Stopped a previous tablet because of ankle swelling" is tagged patient-stated (5.4).
  - Any assessment the model adds is tagged AI inference.
  - The Sinhala summary reads aloud with 5 mg once a day, twice-daily readings for 2 weeks, the 4-week follow-up, and the ECG today, exactly as confirmed.
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

**Run summary:** median latency; number of retries, blocks, and escalations; whether Sinhala recognition and voice were usable at all; glossary gaps found; lines the speaker found unnatural or disrespectful; verdict (ready, needs work, not safe). Copy the summary into `docs/language-benchmark.md`.

## Sign-off

| Role | Name | Checked | Date |
|---|---|---|---|
| Sinhala speaker (all Sinhala lines rewritten and approved) | | [ ] | |
| Clinician (blood pressure explanation, amlodipine 5 mg once a day, home readings, same-day ECG for chest discomfort) | | [ ] | |
| Project lead (rashodkorala) | | [ ] | |
