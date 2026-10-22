# Demo Night Script (19 November 2026)

> **Status: DRAFT for sign-off (demo-night-mvp task 0.4).**
> - Every Punjabi and French line below is Claude's draft. The native speakers must rewrite each one in the words they would naturally say, then sign off.
> - A clinician must check the medical content before rehearsals.
> - Patients and doctors are fictional. Nothing here is medical advice.
> - Beat 5's forced mismatch depends on TDM-002, which is still **proposed**. If it is rejected, play beat 5 without the injection (see beat 5 fallback).

## At a glance

| Item | Detail |
|---|---|
| Scenario | Follow-up one week after an emergency visit for chest pain. Heart attack ruled out; likely angina |
| Plan | Aspirin 81 mg once a day; nitroglycerin spray 0.4 mg, one spray under the tongue when chest pain starts; if not better after 5 minutes, call 911; referral for an angiogram |
| Run 1 | Punjabi: Mr Gurpreet Singh, 58, Brampton |
| Run 2 | French: Mme Lucie Tremblay, 61, Ottawa |
| Length | About 5 minutes per run, about 12 minutes with intro, reset, and close |
| Cast | Narrator (speaks to the audience), Physician "Dr Patel" (team member, English), Patient (native speaker) |

## Kit and set-up

- Demo laptop running `server/` and `web/`; `/control` on the laptop, `/screen` full screen on the TV.
- Two clip-on microphones (physician, patient) or one close-talk microphone passed between them.
- Phone hotspot as primary network; venue wifi as backup.
- Replay log and backup video loaded (TDM-001).
- Presenter mode on the laptop (tamper control; mismatch control if TDM-002 is accepted).

## Fallbacks

| Problem | Action |
|---|---|
| Network drops | Switch to replay mode (TDM-001); narrator says "this is a recording of our rehearsal" |
| Punjabi recognition fails twice in a row | Narrator moves to Run 2 (French) and returns to Punjabi if time allows |
| Anything else breaks | Play the backup video from the current beat |

## Opening (narrator, 30 seconds)

"In Canada, seven in ten recent immigrants have a first language other than English or French. Too often a child ends up interpreting for a parent at the doctor's. Tonight you'll see a consultation where the patient and the doctor share no language, and both of them can trust every word."

---

## Run 1: Punjabi (Mr Gurpreet Singh)

### Beat 1: Language picker (Requirement: Language selection)

- **Physician (on controller):** opens a new visit and selects ਪੰਜਾਬੀ (Punjabi) from the thirteen languages.
- **TV:** language list in each language's own script; Punjabi and French active, others "coming soon".
- **Narrator:** "Thirteen languages are listed in their own scripts. Tonight we use Punjabi and French."

### Beat 2: Consent (Requirement: Consent in the patient's language)

- **TV / patient tablet:** consent notice in Punjabi.
- **Patient:** reads, taps consent.
- **Narrator:** "He gives consent in his own language, before a single word is recorded."

### Beat 3: Live interpretation and empathy (Requirements: Push-to-talk turns, Bilingual captions, Translation is spoken aloud, Tone-preserving translation, Tone labels, Empathy nudge, Patient emotion stays with the physician)

| # | Speaker | Line (English meaning) | Draft line for the native speaker |
|---|---|---|---|
| 3.1 | Physician | "Hello Mr Singh, I'm Dr Patel. This screen shows what we both say, in Punjabi and in English. How have you been since your visit to the emergency department?" | (English, final) |
| 3.2 | Patient | "Sat Sri Akal, doctor. For two weeks, when I climb the stairs, I feel pressure in my chest. It goes away when I sit down." | ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਡਾਕਟਰ ਜੀ। ਪਿਛਲੇ ਦੋ ਹਫ਼ਤਿਆਂ ਤੋਂ ਜਦੋਂ ਮੈਂ ਪੌੜੀਆਂ ਚੜ੍ਹਦਾ ਹਾਂ, ਮੇਰੀ ਛਾਤੀ ਵਿੱਚ ਦਬਾਅ ਜਿਹਾ ਹੁੰਦਾ ਹੈ। ਬੈਠਣ ਨਾਲ ਠੀਕ ਹੋ ਜਾਂਦਾ ਹੈ। |
| 3.3 | Physician | "Your heart tests in the emergency department were reassuring. You did not have a heart attack. The most likely cause is angina: your heart muscle does not get enough blood when you exert yourself." | (English, final) |
| 3.4 | Patient | "Doctor, will I have a heart attack like my father? My father died of a heart attack when he was 55. I am very scared." | ਡਾਕਟਰ ਜੀ, ਕੀ ਮੈਨੂੰ ਵੀ ਮੇਰੇ ਪਿਤਾ ਜੀ ਵਾਂਗ ਦਿਲ ਦਾ ਦੌਰਾ ਪਵੇਗਾ? ਮੇਰੇ ਪਿਤਾ ਜੀ ਪਚਵੰਜਾ ਸਾਲ ਦੀ ਉਮਰ ਵਿੱਚ ਦਿਲ ਦੇ ਦੌਰੇ ਨਾਲ ਗੁਜ਼ਰ ਗਏ ਸਨ। ਮੈਨੂੰ ਬਹੁਤ ਡਰ ਲੱਗਦਾ ਹੈ। |
| 3.5 | Physician (uses the nudge phrase) | "I understand why you are scared, especially after losing your father. We have found this early, and there is a lot we can do." | (English, final) |

- **TV:** each spoken turn side by side, Punjabi and English, with one translation-register label (for example "reassuring" on 3.3 and 3.5, "respectful" on 3.1). No emotion is ever shown.
- **Controller (private):** after 3.4, an empathy nudge: "Patient is frightened about his father's history; acknowledge the fear" with the suggested phrase used in 3.5.
- **Narrator:** after 3.3: "Notice the respectful form of address in Punjabi, and that 'reassuring' carries across." After 3.5: "Only the doctor saw that suggestion. The patient's emotion never appears on the shared screen."
- **Turn 3.4 is the one beat 8 corrects:** if recognition hears "65" (ਪੈਂਹਠ) instead of "55" (ਪਚਵੰਜਾ), leave it for beat 8. If it is recognised correctly, beat 8 shows a confirmation instead (see beat 8).

### Beat 4: Off-the-record pause (Requirement: Off-the-record pause)

| # | Speaker | Line (English meaning) | Draft line for the native speaker |
|---|---|---|---|
| 4.1 | Patient | "Who will see what I say here?" | ਮੇਰੀਆਂ ਗੱਲਾਂ ਕੌਣ ਦੇਖੇਗਾ? |
| 4.2 | Physician | "Only you, me, and your care team. You can pause the recording at any time with that button." | (English, final) |
| 4.3 | Patient | presses pause, waits a few seconds, presses resume | (no speech) |
| 4.4 | Patient | "I have not taken my blood pressure tablets for a month. They made me dizzy, and I was embarrassed to say." | ਮੈਂ ਇੱਕ ਮਹੀਨੇ ਤੋਂ ਬਲੱਡ ਪ੍ਰੈਸ਼ਰ ਦੀਆਂ ਗੋਲੀਆਂ ਨਹੀਂ ਲਈਆਂ। ਉਨ੍ਹਾਂ ਨਾਲ ਚੱਕਰ ਆਉਂਦੇ ਸਨ, ਅਤੇ ਮੈਨੂੰ ਦੱਸਣ ਵਿੱਚ ਸ਼ਰਮ ਆਉਂਦੀ ਸੀ। |
| 4.5 | Physician | "Thank you for telling me. Dizziness is a common side effect, and we can find a tablet that suits you better." | (English, final) |

- **TV:** during 4.3, the paused notice in Punjabi and English; no captions.
- **Narrator:** "While paused, nothing is captured at all. Knowing he is in control, he chose to share something he had been hiding. That openness is the point."

### Beat 5: Blocked dose, then read-back (Requirements: Critical value mismatch blocks speech, Turn outcome precedence, Critical value read-back, Presenter mismatch control)

| # | Speaker | Line | Notes |
|---|---|---|---|
| 5.1 | Presenter | presses the hidden mismatch control (TDM-002) | Not visible on the TV |
| 5.2 | Physician | "Use the nitroglycerin spray: 0.4 milligrams, one spray under your tongue when the chest pain starts." | The injected mismatch survives the retry, so the turn is **blocked** |
| 5.3 | Physician | repeats 5.2 exactly | Values match; controller shows 0.4 mg, one spray, highlighted in both languages; physician confirms; translation spoken |
| 5.4 | Physician | "If the pain is not better after 5 minutes, call 911." | Read-back on "5 minutes" and "911"; confirm; spoken |
| 5.5 | Physician | "Also take one aspirin, 81 milligrams, once a day." | Read-back on 81 mg and once a day; confirm; spoken |

- **TV:** during 5.2, the original English and a "please repeat" notice in both languages, never the wrong translation. During read-back, "checking the dose" in both languages, then the spoken caption with values highlighted.
- **Controller:** after 5.2, the mismatched value shown in both languages and "ask the speaker to repeat".
- **Narrator:** after 5.2: "We forced a translation error there. The system caught that the dose had changed and refused to say it. A wrong dose is never spoken and never shown." After 5.3: "No dose reaches the patient until the doctor confirms it."
- **Fallback if TDM-002 is rejected:** skip 5.1 and 5.2; the narrator explains the rule while 5.3 runs normally.

### Beat 6: Mark high risk and the interpreter (Requirement: Human interpreter offer)

| # | Speaker | Line | Notes |
|---|---|---|---|
| 6.1 | Physician | presses "mark high risk", then says: "I'd like to refer you for a test called an angiogram, which looks at the blood vessels of your heart. Because it is a procedure that needs your consent, I want a qualified interpreter to help us with that conversation." | Interpreter offer appears in both languages |
| 6.2 | Physician | accepts the offer | Simulated connecting state, then "Interpreter would join here (simulated)" |

- **Narrator:** "For high-stakes moments like consent to a procedure, the doctor can bring in a human interpreter in one tap. Tonight the call is simulated; in the product a qualified interpreter joins here."

### Beat 7: Explain-back (Requirement: Explain-back check)

| # | Speaker | Line (English meaning) | Draft line for the native speaker |
|---|---|---|---|
| 7.1 | Physician | "To make sure I explained it well, can you tell me in your own words how you will use these medicines?" | (English, final) |
| 7.2 | Patient | "One aspirin every day. If I have chest pain, I sit down and spray once under my tongue." (leaves out calling 911) | ਹਰ ਰੋਜ਼ ਇੱਕ ਐਸਪਰੀਨ ਲੈਣੀ ਹੈ। ਜੇ ਛਾਤੀ ਵਿੱਚ ਦਰਦ ਹੋਵੇ ਤਾਂ ਬੈਠ ਕੇ ਜੀਭ ਹੇਠਾਂ ਇੱਕ ਸਪਰੇਅ ਕਰਨੀ ਹੈ। |
| 7.3 | Physician | "One more important step: if the pain is not better 5 minutes after the spray, call 911." | (English, final; read-back as in 5.4) |
| 7.4 | Patient | "If the pain does not go after five minutes, I call 911." | ਜੇ ਪੰਜ ਮਿੰਟਾਂ ਵਿੱਚ ਦਰਦ ਠੀਕ ਨਾ ਹੋਵੇ, ਤਾਂ ਮੈਂ 911 ਤੇ ਫ਼ੋਨ ਕਰਾਂਗਾ। |

- **Controller:** after 7.2: aspirin matched, spray matched, "call 911 after 5 minutes" **missed**. After 7.4: all matched.
- **Narrator:** "He left out the most important safety step. The doctor saw it immediately and closed the gap."

### Beat 8: Transcript review (Requirement: Transcript review)

- **Patient (on the review screen):** finds turn 3.4, where "55" was recognised as "65", and re-speaks the correction.

| # | Speaker | Line (English meaning) | Draft line for the native speaker |
|---|---|---|---|
| 8.1 | Patient | "I said fifty-five, not sixty-five." | ਮੈਂ ਪਚਵੰਜਾ ਕਿਹਾ ਸੀ, ਪੈਂਹਠ ਨਹੀਂ। |

- **Review screen:** the corrected turn with its new translation; the history shows the original.
- **Narrator:** "He can check and correct his own words, in Punjabi. The original is never erased."
- **If every turn was recognised correctly live:** the patient confirms turn 3.4 instead, and the narrator says: "Tonight it heard him perfectly. If it hadn't, he could correct it right here, and the original would stay in the history."

### Beat 9: Note, summary, and record verified (Requirements: Note with provenance tags, Patient summary, Record verified badge)

- **Physician (controller):** ends the visit and opens the note. Clicks "Chest pressure on exertion for two weeks" (tagged patient-stated): the source turn 3.2 lights up in Punjabi and English. Points to "Likely stable angina" (tagged AI inference, visually distinct).
- **Patient (review screen):** opens the Punjabi summary and presses listen. The read-aloud includes 81 mg once a day, 0.4 mg spray, and 911 after 5 minutes, exactly as confirmed.
- **TV:** green "record verified" badge. Presenter uses the hidden tamper control on one stored turn: the badge turns red and names the altered turn.
- **Narrator:** "Every sentence in the note says who said it, or that the AI inferred it. His summary is in Punjabi and matches the doses exactly. And if anyone alters the record afterwards, the badge shows it."

**Physician closing line (English, final):** "You did very well today, Mr Singh. You'll get this summary in Punjabi to listen to at home."

---

## Reset between runs (30 seconds)

- Presenter resets the visit (new visit id), restores the tampered record, switches the patient microphone.
- **Narrator:** "Now the same doctor, a different patient, and French: Canada's other official language."

---

## Run 2: French (Mme Lucie Tremblay)

Same nine beats and the same plan. The differences: her empathy moment is about work, her disclosure is different, her explain-back misses a frequency, and her correction is "deux" misheard as "douze". The forced mismatch (beat 5) runs in Run 1 only, so beat 5 here is a normal read-back.

| Beat | # | Speaker | Line (English meaning) | Draft line for the native speaker |
|---|---|---|---|---|
| 1 | | Physician | selects Français | |
| 2 | | Patient | taps consent on the French notice | |
| 3 | 3.1 | Physician | "Hello Ms Tremblay, I'm Dr Patel. This screen shows what we both say, in French and in English. How have you been since the emergency visit?" | (English, final) |
| 3 | 3.2 | Patient | "For two weeks I've had pressure in my chest when I climb the stairs. It passes when I sit down." | Depuis deux semaines, j'ai une pression dans la poitrine quand je monte l'escalier. Ça passe quand je m'assois. |
| 3 | 3.3 | Physician | (same as Run 1, 3.3) | (English, final) |
| 3 | 3.4 | Patient | "I can't miss work. If I take time off, I'll lose my job." | Je ne peux pas manquer le travail. Si je m'absente, je vais perdre mon emploi. |
| 3 | 3.5 | Physician (nudge phrase) | "I hear how worried you are about your job. Let's make a plan that fits around your work." | (English, final) |
| 4 | 4.1 | Patient | "Who will see what I say here?" | Qui va voir ce que je dis ici ? |
| 4 | 4.2 | Physician | (same as Run 1, 4.2) | (English, final) |
| 4 | 4.3 | Patient | presses pause, then resume | (no speech) |
| 4 | 4.4 | Patient | "I had this pain several times before the emergency visit, but I told no one." | J'ai eu ces douleurs plusieurs fois avant l'urgence, mais je n'en ai parlé à personne. |
| 4 | 4.5 | Physician | "Thank you for telling me. That helps me understand what is happening." | (English, final) |
| 5 | 5.3 to 5.5 | Physician | same dose lines as Run 1, each with read-back and confirmation | (English, final) |
| 6 | 6.1 to 6.2 | Physician | same angiogram and "mark high risk" lines as Run 1 | (English, final) |
| 7 | 7.1 | Physician | (same as Run 1, 7.1) | (English, final) |
| 7 | 7.2 | Patient | "I take an aspirin. If I have chest pain, I sit down and spray once under my tongue. If it doesn't pass after five minutes, I call 911." (leaves out "once a day") | Je prends une aspirine. Si j'ai mal à la poitrine, je m'assois et je mets un jet sous la langue. Si ça ne passe pas après cinq minutes, j'appelle le 911. |
| 7 | 7.3 | Physician | "And the aspirin is once a day, every day." | (English, final; read-back) |
| 7 | 7.4 | Patient | "One aspirin a day, every day." | Une aspirine par jour, tous les jours. |
| 8 | 8.1 | Patient | corrects 3.2 if "deux semaines" was heard as "douze semaines": "I said two weeks, not twelve weeks." | J'ai dit deux semaines, pas douze semaines. |
| 9 | | Both | note with tags; French summary read aloud; badge and tamper | |

**Physician closing line (English, final):** "Thank you, Ms Tremblay. Your summary in French will be ready for you to listen to."

## Close (narrator, 30 seconds)

"Two patients, two languages, one doctor. Every dose was confirmed before it was spoken, every word can be checked by the person who said it, and the record proves it hasn't been changed. That's the trust a medical conversation needs, in any language."

---

## Sign-off

| Role | Name | Checked | Date |
|---|---|---|---|
| Punjabi speaker (all Punjabi lines rewritten and approved) | | [ ] | |
| French speaker (all French lines rewritten and approved) | | [ ] | |
| Clinician (medical content: angina explanation, aspirin 81 mg, nitroglycerin 0.4 mg spray and the 5-minute 911 rule, angiogram consent) | | [ ] | |
| Project lead (rashodkorala) | | [ ] | |
