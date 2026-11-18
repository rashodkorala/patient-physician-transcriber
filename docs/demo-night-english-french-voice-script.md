# Demo night voice script | English and Canadian French

One fictional consultation, approximately four to five minutes with time for screen actions.
Dr Patel speaks English, Lucie Tremblay speaks Canadian French, and the narrator speaks English.
The medication line comes from the project's fictional scenario and is for the staged demo only.

Generate each block as its own clip in ElevenLabs, using the same voice for each character throughout.
Copy only the quoted speech into ElevenLabs and name each export with its clip ID.
Play the doctor and patient clips one at a time into the corresponding push-to-talk input on the physician screen.
Hold the button before starting playback and release it after the clip ends.
Let the app provide its own interpreter audio when available.
Use the narrator clips in the video edit or play them between turns, outside microphone capture.
If using prerecorded app output, describe it as a recorded walkthrough.

## 1. Set up the visit and ask for consent

**01 | Narrator | English**

> What happens when a patient and a doctor don't speak the same language? Meet Lucie. She speaks French. Her doctor speaks English. They can each follow this visit in their own language.

**On screen.** Select Français on the physician screen.
Show the French consent notice, then tap **J’accepte** on the patient device before playing the first consultation clip.

## 2. Show speech becoming bilingual captions

**02 | Dr Patel | English**

> Hello, Ms Tremblay. I'm Doctor Patel. How have you been feeling since your visit to the emergency department?

**03 | Lucie | Canadian French**

> Depuis deux semaines, j’ai comme un poids sur la poitrine quand je monte les escaliers. Ça passe quand je m’assois. Ça m’inquiète un peu.

**04 | Narrator | English**

> Lucie says the pressure goes away when she sits down, and that it worries her. The interpreter says that in words, in the same steady voice. Her French stays on the screen alongside the English translation.

**On screen.** Hold on the original and translation columns.
If the physician screen shows a cue that Lucie sounds worried, briefly show it there.

## 3. Let the patient ask for a clearer explanation

**05 | Dr Patel | English**

> I’d like to find out whether the pressure is related to reduced blood flow when you exert yourself.

**On screen.** Tap **Je n’ai pas compris** on the patient device.
Wait for the request to appear on the shared screen and physician view.

**06 | Dr Patel | English**

> Let me say that more simply. You feel the pressure when you climb stairs. I want to find out why it happens when you’re active.

**07 | Narrator | English**

> Lucie asked for a clearer explanation with one tap, in French. Now she can ask to hear that explanation again.

**On screen.** Tap the repeat control and use the app’s replay if audio is working.

## 4. Show the patient controlling the pause

**08 | Lucie | Canadian French**

> J’aimerais faire une petite pause avant de continuer.

**On screen.** Tap **Pause** on the patient device.
Hold on the bilingual pause notice and then tap **Reprendre**.

**09 | Narrator | English**

> Lucie can pause and resume the visit from her own device.

## 5. Catch a simulated dose mismatch

**On screen.** Open **Presenter** on the physician controller and arm the mismatch before playing clip 10.
Cut to the shared screen when the translation is held back.

**10 | Dr Patel | English | Play twice**

> Use the nitroglycerin spray: zero point four milligrams, one spray under your tongue when the chest pain starts.

**11 | Narrator | English | After the first playback**

> We deliberately changed the dose in this simulation. The app flagged the mismatch and held back the translation. The doctor can repeat the instruction and check the amount before it’s spoken.

**On screen.** Replay clip 10.
Show the dose comparison on the physician screen, then select **Confirm and speak** once the displayed values match the fictional script.

## 6. Check what the patient understood

**On screen.** Select **Start explain-back** when it’s available.
Let the app ask the patient to explain the instruction back.

**12 | Lucie | Canadian French**

> Si j’ai mal à la poitrine, j’utilise le vaporisateur.

**13 | Narrator | English**

> Lucie remembered the spray. She left out how much to use and where to spray it. The doctor can clarify those details before they finish.

**14 | Dr Patel | English**

> The part I want to make clear is how to use it. One spray under the tongue.

**15 | Lucie | Canadian French**

> D’accord. Un seul jet sous la langue.

**On screen.** Show the private explain-back result if the run produces it.
Use the app’s closing question if time allows.

## 7. Show the human interpreter option

**16 | Dr Patel | English**

> Before we talk about a procedure and ask for your consent, I’d like a human interpreter to join us.

**On screen.** Mark the discussion as high risk, then request the interpreter.
Show the simulated connection state.

**17 | Narrator | English**

> The doctor can ask for a human interpreter when the conversation needs one. This hand-off is simulated for the demo.

## 8. Close with the record and the French summary

**On screen.** Open transcript review and confirm Lucie’s first turn if it was heard correctly.
If the app heard twelve weeks instead of two, use clip 18 for **Correct by speaking**.
Generate the note and patient summary.
Open a note sentence with a source link, then show the French summary on the patient device if it’s ready.

**18 | Lucie | Canadian French | Optional correction**

> J’ai dit deux semaines, pas douze semaines.

**19 | Narrator | English**

> Lucie can review what the app heard and see a summary in French. The doctor can open a note sentence and trace it back to the conversation.

**20 | Narrator | English | Closing**

> The goal is a visit both people can follow, with a way to ask for clarity and check the details that matter.

## Short video cut

For a 60 to 90 second cut, use clips 01, 03, 05, 06, 10, 11, and 20.
Show the French consent tap, the bilingual captions, **Je n’ai pas compris**, and the blocked-dose notice.
Show the successful dose confirmation as a quick final visual before the closing line.
