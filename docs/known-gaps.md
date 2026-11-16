# Known gaps

> - Status: recorded, not fixed (MDD-006, decision 6).
> - Last updated: 16 November 2026, with the `affect-in-words` change.

These are limits of the demo-night prototype that we know about and have chosen not to fix yet.
Each one is stated plainly so nobody mistakes the prototype for more than it is.

## Affect is read from the words only

The interpreter reads how the patient feels from the words they said, not from how they sounded.
Speech recognition gives us text, not tone of voice, so the audio's prosody never reaches the model.
Neutral words said in a worried voice are therefore read as plain, and the relay to the physician carries no affect phrase.
This is why the phrase is hedged ("sounding worried", never "is worried"): it is the model's reading of the words, not a fact about the patient.
The physician's controller shows the same reading as a label, so the physician can see what the interpreter based it on.

## Hosted APIs, not our own models

The product runs on hosted APIs: Claude for translation and the checks, ElevenLabs for the voice, and Azure for speech recognition and the fallback voice.
It does not use models of our own, hosted on AWS, and trained on real consultation data.
Quality, latency, cost, and data handling all depend on those vendors for now.
Compliance, data residency, and vendor terms are deliberately not weighed at this stage, by the project lead's decision.

## The voice is not expressive

The interpreter speaks every turn and every interpreter line in one constant delivery.
We tried varying the voice by the physician's manner and the patient's emotion, and testing showed the voice did not carry it, so it was removed (MDD-006, IDR-006).
Certainty is no longer audible in the voice either; it is carried by the words only.

## The affect phrase is spoken in the room

For a patient or companion turn whose affect is clearly not plain, the relay to the physician opens with one hedged phrase, for example "The patient says, sounding worried, ...".
That phrase is spoken aloud in the room in the physician's language, so the patient and anyone else present can hear it.
Because the shown text and the spoken text are the same, the phrase also appears inside the translation on the shared screen, on the patient's device, and in the record.
The patient's manner and emotion never appear as a label anywhere but the physician's controller.

## Not yet reviewed by native speakers

How the affect phrase reads in the physician's language, and in the reporting frames used for each patient language pair, has not been reviewed by native speakers.
The phrase is English-first in practice, and the fake model used in tests writes it in English only.
That review is an end-of-project task (`affect-in-words` task 7.1), run only when the project lead asks.
