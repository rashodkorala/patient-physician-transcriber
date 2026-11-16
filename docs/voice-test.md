# Mediator voice test (mediator-voice tasks 0.4 and 2.3)

> **Status: automated run recorded; native speaker ratings and the listening test are pending.**

## Relay run, 3 November 2026

- Pipeline: the live turn graph (`server/graph/turn_graph.py`) with Claude, names set to Dr. Patel, Gurpreet Singh, and Lucie Tremblay.
- Lines: the demo script (`docs/demo-script.md`), both directions, typed with recognition confidence 1.0.
- Runner: a scratch script calling `TurnPipeline.run` directly, with no speech and no browser.

### What the run shows

- Every relay uses one reported-speech frame naming the speaker, in indirect speech, with "they" for people whose gender was not given.
- Instructions keep their force: "call 911" is relayed as "you should call 911" in both languages.
- Doses, frequencies, and the 911 instruction match on the first attempt (5.3 and 5.4 in Punjabi, 5.4 in French).
- Three turns are blocked: 3.4, 5.5, and 7.2 in Punjabi.
  In each one the relay is correct, but the critical value check does not read a Punjabi number word in it: ਪਚਵੰਜਾ (55), and ਇੱਕ (one) before a medicine name.
  The same gap blocks French "une aspirine".
  This sits in `server/critical_values.py`, which has uncommitted work in progress on native number words, and needs fixing there before demo-quality runs.
- French 7.4 needed a second attempt, so it took longer.

### Relays

Native speakers fill in the last two columns: faithful means nothing was lost, added, or softened; natural means it sounds like a person interpreting.

| Line | Speaker | Said | Relay | Back-translation | Outcome (attempts) | Critical values | Seconds | Faithful (1-5) | Natural (1-5) |
|---|---|---|---|---|---|---|---|---|---|
| pa-IN 3.1 | physician | Hello Mr Singh, I'm Dr Patel. This screen shows what we both say, in Punjabi and in English. How have you been since your visit to the emergency department? | ਡਾਕਟਰ ਪਟੇਲ ਕਹਿ ਰਹੇ ਹਨ ਕਿ ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਸਿੰਘ ਜੀ, ਉਹ ਡਾਕਟਰ ਪਟੇਲ ਹਨ। ਇਹ ਸਕਰੀਨ ਦਿਖਾਉਂਦੀ ਹੈ ਕਿ ਤੁਸੀਂ ਦੋਵੇਂ ਕੀ ਕਹਿੰਦੇ ਹੋ, ਪੰਜਾਬੀ ਵਿੱਚ ਅਤੇ ਅੰਗਰੇਜ਼ੀ ਵਿੱਚ। ਉਹ ਪੁੱਛ ਰਹੇ ਹਨ ਕਿ ਐਮਰਜੈਂਸੀ ਵਿਭਾਗ ਵਿੱਚ ਤੁਹਾਡੀ ਫੇਰੀ ਤੋਂ ਬਾਅਦ ਤੁਸੀਂ ਕਿਵੇਂ ਰਹੇ ਹੋ? | Dr. Patel is saying hello Mr. Singh, and that they are Dr. Patel. This screen shows what the two of you say, in Punjabi and in English. They are asking how you have been since your visit to the emergency department. | final (1) | none | 5.4 |  |  |
| pa-IN 3.2 | patient | ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਡਾਕਟਰ ਜੀ। ਪਿਛਲੇ ਦੋ ਹਫ਼ਤਿਆਂ ਤੋਂ ਜਦੋਂ ਮੈਂ ਪੌੜੀਆਂ ਚੜ੍ਹਦਾ ਹਾਂ, ਮੇਰੀ ਛਾਤੀ ਵਿੱਚ ਦਬਾਅ ਜਿਹਾ ਹੁੰਦਾ ਹੈ। ਬੈਠਣ ਨਾਲ ਠੀਕ ਹੋ ਜਾਂਦਾ ਹੈ। | Gurpreet Singh is saying sat sri akal, doctor (a traditional Punjabi Sikh greeting). For the last 2 weeks, whenever they climb stairs, they get a kind of pressure in their chest. It gets better when they sit down. | Gurpreet Singh is saying sat sri akal, doctor. For the past 2 weeks, when they climb stairs, there is a kind of pressure in their chest. It gets better with sitting. | final (1) | ਦੋ ਹਫ਼ਤਿਆਂ -> 2 weeks ok | 4.0 |  |  |
| pa-IN 3.3 | physician | Your heart tests in the emergency department were reassuring. You did not have a heart attack. The most likely cause is angina: your heart muscle does not get enough blood when you exert yourself. | ਡਾਕਟਰ ਪਟੇਲ ਕਹਿ ਰਹੇ ਹਨ ਕਿ ਐਮਰਜੈਂਸੀ ਵਿਭਾਗ ਵਿੱਚ ਤੁਹਾਡੇ ਦਿਲ ਦੇ ਟੈਸਟ ਤਸੱਲੀਬਖ਼ਸ਼ ਸਨ। ਤੁਹਾਨੂੰ ਦਿਲ ਦਾ ਦੌਰਾ ਨਹੀਂ ਪਿਆ ਸੀ। ਸਭ ਤੋਂ ਸੰਭਾਵਿਤ ਕਾਰਨ ਐਨਜਾਈਨਾ (ਛਾਤੀ ਦਾ ਦਰਦ) ਹੈ, ਯਾਨੀ ਜਦੋਂ ਤੁਸੀਂ ਜ਼ੋਰ ਲਾਉਂਦੇ ਹੋ ਤਾਂ ਤੁਹਾਡੇ ਦਿਲ ਦੀ ਮਾਸਪੇਸ਼ੀ ਨੂੰ ਲੋੜੀਂਦਾ ਖੂਨ ਨਹੀਂ ਮਿਲਦਾ। | Dr. Patel is saying that your heart tests in the emergency department were reassuring. You did not have a heart attack. The most likely cause is angina (chest pain), that is, when you exert yourself, your heart muscle does not get enough blood. | final (1) | none | 6.1 |  |  |
| pa-IN 3.4 | patient | ਡਾਕਟਰ ਜੀ, ਕੀ ਮੈਨੂੰ ਵੀ ਮੇਰੇ ਪਿਤਾ ਜੀ ਵਾਂਗ ਦਿਲ ਦਾ ਦੌਰਾ ਪਵੇਗਾ? ਮੇਰੇ ਪਿਤਾ ਜੀ ਪਚਵੰਜਾ ਸਾਲ ਦੀ ਉਮਰ ਵਿੱਚ ਦਿਲ ਦੇ ਦੌਰੇ ਨਾਲ ਗੁਜ਼ਰ ਗਏ ਸਨ। ਮੈਨੂੰ ਬਹੁਤ ਡਰ ਲੱਗਦਾ ਹੈ। | Gurpreet Singh is asking whether they will also have a heart attack, like their father. Their father passed away from a heart attack at the age of 55. They are very scared. | ਗੁਰਪ੍ਰੀਤ ਸਿੰਘ ਪੁੱਛ ਰਹੇ ਹਨ ਕਿ ਕੀ ਉਨ੍ਹਾਂ ਨੂੰ ਵੀ ਆਪਣੇ ਪਿਤਾ ਜੀ ਵਾਂਗ ਦਿਲ ਦਾ ਦੌਰਾ ਪਵੇਗਾ। ਉਨ੍ਹਾਂ ਦੇ ਪਿਤਾ ਜੀ 55 ਸਾਲ ਦੀ ਉਮਰ ਵਿੱਚ ਦਿਲ ਦੇ ਦੌਰੇ ਨਾਲ ਗੁਜ਼ਰ ਗਏ ਸਨ। ਉਨ੍ਹਾਂ ਨੂੰ ਬਹੁਤ ਡਰ ਲੱਗਦਾ ਹੈ। | blocked (2) | - -> 55 MISMATCH | 14.0 |  |  |
| pa-IN 3.5 | physician | I understand why you are scared, especially after losing your father. We have found this early, and there is a lot we can do. | ਡਾਕਟਰ ਪਟੇਲ ਕਹਿ ਰਹੇ ਹਨ ਕਿ ਉਹ ਸਮਝਦੇ ਹਨ ਕਿ ਤੁਸੀਂ ਕਿਉਂ ਡਰੇ ਹੋਏ ਹੋ, ਖ਼ਾਸ ਕਰਕੇ ਆਪਣੇ ਪਿਤਾ ਜੀ ਨੂੰ ਗੁਆਉਣ ਤੋਂ ਬਾਅਦ। ਉਹ ਇਹ ਵੀ ਕਹਿ ਰਹੇ ਹਨ ਕਿ ਇਹ ਸਮੇਂ ਸਿਰ, ਯਾਨੀ ਸ਼ੁਰੂ ਵਿੱਚ ਹੀ ਪਤਾ ਲੱਗ ਗਿਆ ਹੈ, ਅਤੇ ਬਹੁਤ ਕੁਝ ਕੀਤਾ ਜਾ ਸਕਦਾ ਹੈ। | Dr. Patel is saying that they understand why you are scared, especially after losing your father. They are also saying that this has been found in time, that is, early, and that a lot can be done. | final (1) | none | 5.2 |  |  |
| pa-IN 4.4 | patient | ਮੈਂ ਇੱਕ ਮਹੀਨੇ ਤੋਂ ਬਲੱਡ ਪ੍ਰੈਸ਼ਰ ਦੀਆਂ ਗੋਲੀਆਂ ਨਹੀਂ ਲਈਆਂ। ਉਨ੍ਹਾਂ ਨਾਲ ਚੱਕਰ ਆਉਂਦੇ ਸਨ, ਅਤੇ ਮੈਨੂੰ ਦੱਸਣ ਵਿੱਚ ਸ਼ਰਮ ਆਉਂਦੀ ਸੀ। | Gurpreet Singh is saying they have not taken their blood pressure pills for 1 month. They are saying the pills made them dizzy, and they felt embarrassed to tell you. | Gurpreet Singh is saying they have not taken their blood pressure pills for 1 month. They are saying the pills were causing dizziness, and they felt embarrassed to tell you. | final (1) | ਇੱਕ ਮਹੀਨੇ -> 1 month ok | 3.7 |  |  |
| pa-IN 5.3 | physician | Use the nitroglycerin spray: 0.4 milligrams, one spray under your tongue when the chest pain starts. | ਡਾਕਟਰ ਪਟੇਲ ਜੀ ਕਹਿ ਰਹੇ ਹਨ ਕਿ ਤੁਸੀਂ ਨਾਈਟ੍ਰੋਗਲਿਸਰੀਨ ਸਪਰੇਅ ਵਰਤੋ: 0.4 ਮਿਲੀਗ੍ਰਾਮ, ਜਦੋਂ ਛਾਤੀ ਦਾ ਦਰਦ ਸ਼ੁਰੂ ਹੋਵੇ ਤਾਂ ਆਪਣੀ ਜੀਭ ਦੇ ਥੱਲੇ 1 ਸਪਰੇਅ ਕਰੋ। | Dr. Patel is saying that you should use the nitroglycerin spray: 0.4 milligrams, and when the chest pain starts, you should give 1 spray under your tongue. | readback_required (1) | 0.4 milligrams -> 0.4 ਮਿਲੀਗ੍ਰਾਮ ok, one spray -> 1 ਸਪਰੇਅ ok, nitroglycerin spray -> ਨਾਈਟ੍ਰੋਗਲਿਸਰੀਨ ਸਪਰੇਅ ok | 3.8 |  |  |
| pa-IN 5.4 | physician | If the pain is not better after 5 minutes, call 911. | ਡਾਕਟਰ ਪਟੇਲ ਕਹਿ ਰਹੇ ਹਨ ਕਿ ਜੇ 5 ਮਿੰਟ ਬਾਅਦ ਵੀ ਦਰਦ ਠੀਕ ਨਾ ਹੋਵੇ, ਤਾਂ ਤੁਹਾਨੂੰ 911 'ਤੇ ਫ਼ੋਨ ਕਰਨਾ ਚਾਹੀਦਾ ਹੈ। | Dr. Patel is saying that if the pain is not better even after 5 minutes, you should call 911. | readback_required (1) | 5 minutes -> 5 ਮਿੰਟ ok, 911 -> 911 ok | 3.9 |  |  |
| pa-IN 5.5 | physician | Also take one aspirin, 81 milligrams, once a day. | ਡਾਕਟਰ ਪਟੇਲ ਕਹਿ ਰਹੇ ਹਨ ਕਿ ਤੁਹਾਨੂੰ ਇਸ ਦੇ ਨਾਲ ਇੱਕ ਐਸਪਰੀਨ, 81 ਮਿਲੀਗ੍ਰਾਮ, ਦਿਨ ਵਿੱਚ ਇੱਕ ਵਾਰ ਲੈਣੀ ਚਾਹੀਦੀ ਹੈ। | Dr. Patel is saying that you should also take one aspirin, 81 milligrams, once a day. | blocked (2) | one -> - MISMATCH, 81 milligrams -> 81 ਮਿਲੀਗ੍ਰਾਮ ok, once a day -> ਦਿਨ ਵਿੱਚ ਇੱਕ ਵਾਰ ok, aspirin -> ਐਸਪਰੀਨ ok | 10.1 |  |  |
| pa-IN 7.2 | patient | ਹਰ ਰੋਜ਼ ਇੱਕ ਐਸਪਰੀਨ ਲੈਣੀ ਹੈ। ਜੇ ਛਾਤੀ ਵਿੱਚ ਦਰਦ ਹੋਵੇ ਤਾਂ ਬੈਠ ਕੇ ਜੀਭ ਹੇਠਾਂ ਇੱਕ ਸਪਰੇਅ ਕਰਨੀ ਹੈ। | Gurpreet Singh is saying they have to take 1 aspirin every day. If they have chest pain, they have to sit down and use 1 spray under the tongue. | ਗੁਰਪ੍ਰੀਤ ਸਿੰਘ ਕਹਿ ਰਹੇ ਹਨ ਕਿ ਉਨ੍ਹਾਂ ਨੂੰ ਹਰ ਰੋਜ਼ 1 ਐਸਪਰੀਨ ਲੈਣੀ ਹੈ। ਜੇ ਉਨ੍ਹਾਂ ਦੀ ਛਾਤੀ ਵਿੱਚ ਦਰਦ ਹੋਵੇ ਤਾਂ ਉਨ੍ਹਾਂ ਨੂੰ ਬੈਠ ਕੇ ਜੀਭ ਹੇਠਾਂ 1 ਸਪਰੇਅ ਕਰਨੀ ਹੈ। | blocked (2) | ਇੱਕ ਸਪਰੇਅ -> 1 spray ok, - -> 1 MISMATCH, ਹਰ ਰੋਜ਼ -> every day ok, ਐਸਪਰੀਨ -> aspirin ok | 14.3 |  |  |
| fr-CA 3.2 | patient | Depuis deux semaines, j'ai une pression dans la poitrine quand je monte l'escalier. Ça passe quand je m'assois. | Lucie Tremblay is saying that for the past 2 weeks they have had a pressure in their chest when they climb the stairs. They are saying it goes away when they sit down. | Lucie Tremblay dit que depuis 2 semaines, elle ou il a une pression dans la poitrine quand la personne monte l'escalier. Elle ou il dit que ça passe quand la personne s'assoit. | final (1) | deux semaines -> 2 weeks ok | 4.0 |  |  |
| fr-CA 3.4 | patient | Je ne peux pas manquer le travail. Si je m'absente, je vais perdre mon emploi. | Lucie Tremblay is saying they can't miss work. They're saying that if they are absent, they will lose their job. | Lucie Tremblay dit qu'elle ou il ne peut pas manquer le travail. Elle ou il dit que si elle ou il s'absente, elle ou il va perdre son emploi. | final (1) | none | 3.7 |  |  |
| fr-CA 4.1 | patient | Qui va voir ce que je dis ici ? | Lucie Tremblay is asking who will see what they say here. | Lucie Tremblay demande qui va voir ce qu'elle ou il dit ici. | final (1) | none | 3.7 |  |  |
| fr-CA 5.4 | physician | If the pain is not better after 5 minutes, call 911. | Le docteur Patel dit que si la douleur n'est pas meilleure après 5 minutes, vous devriez appeler le 911. | Dr. Patel is saying that if the pain is not better after 5 minutes, you should call 911. | readback_required (1) | 5 minutes -> 5 minutes ok, 911 -> 911 ok | 3.3 |  |  |
| fr-CA 7.4 | patient | Une aspirine par jour, tous les jours. | Lucie Tremblay is saying that they take an aspirin a day, every day. | Lucie Tremblay dit qu'elle ou il prend une aspirine par jour, tous les jours. | final (2) | tous les jours -> every day ok, aspirine -> aspirine ok | 6.6 |  |  |
| fr-CA 7.1 | physician | To make sure I explained it well, can you tell me in your own words how you will use these medicines? | Le Dr Patel dit que, pour s'assurer d'avoir bien expliqué, il ou elle vous demande si vous pouvez dire avec vos propres mots comment vous allez utiliser ces médicaments. | Dr. Patel is saying that, to make sure they explained well, they are asking whether you can say in your own words how you will use these medicines. | final (1) | none | 3.5 |  |  |

## Name reading, 3 November 2026 (task 2.6)

- Model: the tone-check model (Haiku), through `read_name` in `server/introduction.py`.
- Replies were typed, not spoken: speech recognition of names, especially Punjabi names, still needs a test with the speakers.
- Result: 15 of 15 read correctly, including Gurmukhi names written in Latin script ("ਮੇਰਾ ਨਾਮ ਗੁਰਪ੍ਰੀਤ ਸਿੰਘ ਹੈ।" as "Gurpreet Singh") and replies with no name ("Pardon, je n'ai pas compris." gives none).

| Role | Reply | Name read |
|---|---|---|
| Physician | I'm Doctor Thomas. | Dr. Thomas |
| Physician | Just call me Priya. | Priya |
| Physician | Dr. Patel, please. | Dr. Patel |
| Physician | Um, it's Doctor Anne-Marie Leblanc | Dr. Anne-Marie Leblanc |
| Physician | Sorry, can you repeat that? | (none) |
| Patient | ਮੇਰਾ ਨਾਮ ਗੁਰਪ੍ਰੀਤ ਸਿੰਘ ਹੈ। | Gurpreet Singh |
| Patient | ਜੀ, ਹਰਪ੍ਰੀਤ ਕੌਰ। | Harpreet Kaur |
| Patient | ਮੈਨੂੰ ਬਲਜੀਤ ਕਹਿ ਸਕਦੇ ਹੋ। | Baljit |
| Patient | ਸਤ ਸ੍ਰੀ ਅਕਾਲ, ਮੈਂ ਅਮਨਦੀਪ ਹਾਂ। | Amandeep |
| Patient | ਕੀ ਕਿਹਾ ਤੁਸੀਂ? | (none) |
| Patient | Je m'appelle Lucie Tremblay. | Lucie Tremblay |
| Patient | Lucie, s'il vous plaît. | Lucie |
| Patient | Moi c'est Jean-François. | Jean-François |
| Patient | Appelez-moi Madame Gagnon. | Madame Gagnon |
| Patient | Pardon, je n'ai pas compris. | (none) |

## Listening test (task 0.4)

Pending: a blind comparison with the Punjabi and French speakers, then the chosen voice per language and the verdict here.

### How to run it

1. Put the keys in `server/.env`: `OPENAI_API_KEY`, `ELEVENLABS_API_KEY` (optionally `ELEVENLABS_VOICE_ID`), `AZURE_SPEECH_KEY`, and `AZURE_SPEECH_REGION`.
2. From `server/`, run `uv run python scripts/voice_samples.py`.
   It speaks every relay above with each voice and writes `server/voice-samples/index.html`, which git ignores.
3. Each line's clips are shuffled under A, B, and C, so the speakers do not know the vendor.
   Open `server/voice-samples/key.json` only after the ratings are recorded.

### What each vendor says it supports, checked 3 November 2026

| | OpenAI `gpt-4o-mini-tts` | ElevenLabs `eleven_v4` | Azure (current) |
|---|---|---|---|
| Punjabi | Not in OpenAI's language list | Listed | `pa-IN-VaaniNeural` |
| French | Listed (no Canadian French) | Listed (no Canadian French) | `fr-CA-SylvieNeural` |
| Tone control | Plain-language `instructions` | Audio tags such as `[measured]`; stability setting | SSML styles for some voices |
| Status | Deprecated: shuts down 6 January 2027, with OpenAI pointing to its Realtime API | Under active development | In use |

Sources: OpenAI's [text to speech guide](https://developers.openai.com/api/docs/guides/text-to-speech), ElevenLabs' [Eleven v4 page](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/eleven-v4) and [language list](https://elevenlabs.io/docs/help-center/other/what-languages-do-you-support).

## Tamil relay run, 6 November 2026 (TDM-004)

- Pipeline: the live turn graph with Claude, names set to Dr. Patel and Meena Rajaratnam.
- Lines: `docs/test-script-tamil.md`, both directions, typed with recognition confidence 1.0.
- First run, before the fix: 3 of 10 correct relays were blocked, because the critical value check did not read Tamil units (மில்லிகிராம், நிமிடங்கள்) or number words (ஐம்பத்து நான்கு).
- Second run, after adding Tamil units, numbers, and frequencies to `server/critical_values.py`: 0 of 11 blocked, all on the first attempt but 3.3.

| Line | Speaker | Outcome | Critical values | Seconds | Faithful (1-5) | Natural (1-5) |
|---|---|---|---|---|---|---|
| ta-LK 3.2 | patient | final | none | 3.8 |  |  |
| ta-LK 3.3 | patient | final | ஐம்பத்து நான்கு வயது -> fifty-four years ok | 7.4 |  |  |
| ta-LK 4.2 | physician | readback_required | 2 -> 2 ok | 4.3 |  |  |
| ta-LK 5.1 | patient | final | none | 3.8 |  |  |
| ta-LK 6.4 | patient | final | none | 3.6 |  |  |
| ta-LK 6.5 | physician | final | none | 5.0 |  |  |
| ta-LK 7.3 | physician | readback_required | 500 milligrams -> 500 மில்லிகிராம் ok, twice a day -> ஒரு நாளைக்கு 2 முறை ok, metformin -> மெட்ஃபோர்மின் ok | 3.7 |  |  |
| ta-LK 7.4 | physician | readback_required | 3 months -> 3 மாதங்களில் ok | 4.4 |  |  |
| ta-LK 7.5 | physician | readback_required | 30 minutes -> 30 நிமிடங்கள் ok, every day -> ஒவ்வொரு நாளும் ok | 3.6 |  |  |
| ta-LK 8.2 | patient | final | ஒரு மாத்திரை -> one tablet ok (twice), தினமும் -> every day ok | 3.6 |  |  |
| ta-LK 8.4 | patient | final | none | 3.4 |  |  |

- 6.4 keeps the religious sense of விரதம் ("vratham, a religious fast"), as the script asks.
- The HbA1c gloss was changed from "மூன்று மாத" (three-month) to "நீண்டகால" (long-term), so the gloss no longer adds a number the physician did not say.
- ElevenLabs `eleven_v4` with `language_code` `ta` spoke relay 7.3 (first audio 1.2 s) and the introduction line (0.7 s); a Tamil speaker still has to judge the voice.

## Trust layer run, 11 November 2026 (trust-across-the-barrier task 5.2)

- Server: the real app (`uvicorn main:create_app --factory`) with `server/.env` and `.env.local` loaded.
  Its start-up line: "Translator: Claude (claude-sonnet-5-5, tone check claude-haiku-5-5). Speech: Azure, voice ElevenLabs (eleven_v4) with Azure fallback."
  The voice is the default account voice (Sarah), since no `ELEVENLABS_VOICE_ID` is set; embeddings are E5.
- Visit: Punjabi (pa-IN) and English (en-CA), names Dr Patel and Gurpreet Singh, consent given from the patient's device (the review connection).
- Runner: a scratch Node script with raw WebSocket connections as a controller, a shared screen, and the patient's device, as `web/e2e/visit-steps.mjs` `socket()` does.
  Turns were typed with recognition confidence 1.0, not spoken, and no browser played the audio.
- Leak check: the screen and the patient's device received no `turn.analysis`, `trust.update`, or `empathy.nudge`, and no `trust` in any `visit.state`.
  Both received both `patient.signal` events, and every caption the screen received carried the manner the controller saw.

### Turns

Punjabi relays are drafts for the native speaker to rate, as in the runs above.
Manner is the physician's manner read from the words; for patient and companion turns it stays private, and their captions carry no manner.

| # | Speaker | Said | Manner | Emotion | Certainty | Status (attempts) | Relay | Back-translation | Seconds |
|---|---|---|---|---|---|---|---|---|---|
| 1 | physician | Hello Mr Singh, I'm Dr Patel. How have you been since your visit to the emergency department? | warm | calm | high | final (1) | ਡਾਕਟਰ ਪਟੇਲ ਜੀ ਤੁਹਾਨੂੰ ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਕਹਿ ਰਹੇ ਹਨ, ਸਿੰਘ ਜੀ, ਅਤੇ ਦੱਸ ਰਹੇ ਹਨ ਕਿ ਉਹ ਡਾਕਟਰ ਪਟੇਲ ਹਨ। ਉਹ ਪੁੱਛ ਰਹੇ ਹਨ ਕਿ ਐਮਰਜੈਂਸੀ ਵਿਭਾਗ ਵਿੱਚ ਆਉਣ ਤੋਂ ਬਾਅਦ ਤੁਸੀਂ ਕਿਵੇਂ ਰਹੇ ਹੋ? | Dr Patel is saying hello to you, Mr Singh, and is telling you that they are Dr Patel. They are asking how you have been since your visit to the emergency department. | 7.2 |
| 2 | patient | ਡਾਕਟਰ ਜੀ, ਕੀ ਮੈਨੂੰ ਵੀ ਮੇਰੇ ਪਿਤਾ ਜੀ ਵਾਂਗ ਦਿਲ ਦਾ ਦੌਰਾ ਪਵੇਗਾ? ਮੈਨੂੰ ਬਹੁਤ ਡਰ ਲੱਗਦਾ ਹੈ। | plain | worried | low | final (1) | Gurpreet Singh is asking, Doctor, whether you think they will also have a heart attack like their father did. They are saying they are very scared. | Gurpreet Singh is asking, Doctor, whether they will also have a heart attack like their father did. They are saying they are very scared. | 4.5 |
| 3 | physician | I understand why you are scared, especially after losing your father. Your heart tests were reassuring. You did not have a heart attack, and we have found this early. | reassuring | calm | high | final (1) | ਡਾਕਟਰ ਪਟੇਲ ਕਹਿ ਰਹੇ ਹਨ, ਤਸੱਲੀ ਨਾਲ, ਕਿ ਉਹ ਸਮਝਦੇ ਹਨ ਕਿ ਤੁਸੀਂ ਕਿਉਂ ਡਰੇ ਹੋਏ ਹੋ, ਖ਼ਾਸ ਕਰਕੇ ਆਪਣੇ ਪਿਤਾ ਜੀ ਨੂੰ ਗੁਆਉਣ ਤੋਂ ਬਾਅਦ। ਤੁਹਾਡੇ ਦਿਲ ਦੇ ਟੈਸਟ ਤਸੱਲੀ ਦੇਣ ਵਾਲੇ ਸਨ। ਤੁਹਾਨੂੰ ਦਿਲ ਦਾ ਦੌਰਾ ਨਹੀਂ ਪਿਆ, ਅਤੇ ਅਸੀਂ ਇਹ ਜਲਦੀ ਲੱਭ ਲਿਆ ਹੈ। | Dr Patel is saying, reassuringly, that they understand why you are scared, especially after losing your father. Your heart tests were reassuring. You did not have a heart attack, and we have found this early. | 6.0 |
| 4 | patient | ਠੀਕ ਹੈ ਡਾਕਟਰ ਜੀ, ਇਹ ਸੁਣ ਕੇ ਮੈਨੂੰ ਕੁਝ ਰਾਹਤ ਮਿਲੀ। | plain | relieved | medium | final (1) | Gurpreet Singh is saying, okay doctor, that hearing this has given them some relief. | Gurpreet Singh is saying that, okay doctor, hearing this has given them some relief. | 4.0 |
| 5 | physician | Can I ask, do you drink alcohol, even occasionally? | plain | calm | high | final (1) | ਡਾਕਟਰ ਪਟੇਲ ਪੁੱਛ ਰਹੇ ਹਨ ਕਿ ਕੀ ਤੁਸੀਂ ਸ਼ਰਾਬ ਪੀਂਦੇ ਹੋ, ਭਾਵੇਂ ਕਦੇ-ਕਦੇ ਹੀ ਸਹੀ? | Dr Patel is asking whether you drink alcohol, even if only occasionally. | 4.4 |
| 6 | physician | If the pain is not better after 5 minutes, call 911. | plain | calm | high | readback_required (1), confirmed | ਡਾਕਟਰ ਪਟੇਲ ਕਹਿ ਰਹੇ ਹਨ ਕਿ ਜੇ 5 ਮਿੰਟ ਬਾਅਦ ਵੀ ਤੁਹਾਡਾ ਦਰਦ ਠੀਕ ਨਾ ਹੋਵੇ, ਤਾਂ ਤੁਹਾਨੂੰ 911 ਨੂੰ ਫ਼ੋਨ ਕਰਨਾ ਚਾਹੀਦਾ ਹੈ। | Dr Patel is saying that if your pain is not better after 5 minutes, you should call 911. | 4.7 |
| 7 | companion | ਉਹ ਰਾਤ ਨੂੰ ਵੀ ਸਾਹ ਚੜ੍ਹਨ ਦੀ ਸ਼ਿਕਾਇਤ ਕਰਦੇ ਹਨ। | plain | worried | high | final (1) | The patient's companion is saying that the patient also complains of shortness of breath at night. | The patient's companion is saying that the patient also complains of shortness of breath at night. | 4.0 |

- Seconds run from `turn.submit` to `turn.result` on the controller; for turn 6 they include the read-back confirmation.
  Each turn is one translate call on Sonnet (2.4 to 4.8 s) and one tone check on Haiku (1.3 to 2.2 s).
- Turn 6's critical values matched on the first attempt: 5 minutes to 5 ਮਿੰਟ, and 911 to 911.
- The captions carried `warm`, `reassuring`, `plain`, and `plain` for turns 1, 3, 5, and 6, and `null` for turns 2, 4, and 7.

### Trust updates on the controller

| Turn | Speaker | Emotion | Manner | reassuranceLanded | Cue |
|---|---|---|---|---|---|
| 1 | physician | - | warm | null | none |
| 2 | patient | worried | plain | null | reassurance: "Acknowledge the family's fear directly and gently before answering the heart attack question." |
| 3 | physician | - | reassuring | null | culture: "Sensitive: the patient is grieving her father's heart death. Naming the grief is good, but say the finding plainly. Consider noting that the tests show no heart attack, so she is not at the same risk " (cut at 200 characters) |
| 4 | patient | relieved | plain | **true** | none |
| 5 | physician | - | plain | null | culture: "Alcohol is a sensitive topic here. Ask gently, without judgement, and explain it matters for safe medicine dosing and liver health. Address the patient directly, not family." |
| 6 | physician | - | plain | null | none |
| after 6 | signal `not_understood` | - | - | null | understanding: "Say it another way, in shorter sentences, one instruction at a time." |
| after 6 | signal `slower` | - | - | null | understanding: "Slow down and pause between sentences." |
| 7 | companion | worried | plain | null | none (a companion turn gets neither a nudge nor a cue) |

- Turn 2 also produced an `empathy.nudge` to the controller, with the phrase "I understand why you are scared, especially with what happened to your father."
- Each trust update arrived 1.2 to 4.6 s after its turn, off the turn's critical path.

### Signals and interpreter lines

- `not_understood` and then `slower`, three seconds apart from the patient's device, both accepted with `afterTurnId` set to turn 6, and both shown to every role.
- Lines said to the physician, in English only: "Gurpreet Singh is saying they did not understand that. Could you say it another way?" and "Gurpreet Singh is asking you to speak more slowly."
- The closing check (`visit.ask_if_clear`), Punjabi first and English shown: "Gurpreet Singh ਜੀ, ਕੀ ਅੱਜ ਡਾਕਟਰ ਜੀ ਨੇ ਕੋਈ ਅਜਿਹੀ ਗੱਲ ਕਹੀ ਹੈ ਜੋ ਤੁਸੀਂ ਦੁਬਾਰਾ ਸਮਝਣਾ ਚਾਹੋਗੇ?" and "Gurpreet Singh, is there anything the doctor said today that you would like explained again?"
  The Punjabi line keeps the name in Latin script, as typed; the native speaker should hear how the voice reads it.

### Voice fetches

The server log does not print the delivery; the delivery below is what `delivery_for_turn` in `server/voice.py` gave at the time for each turn's manner, emotion, and certainty.
Since 16 November 2026 there is no such table: every turn and every interpreter line is spoken in one constant delivery (`[calm]`, stability 0.55), because the varied deliveries did not carry the tone, and a patient's affect is now carried in words instead (MDD-006, IDR-006).

| Speech | Language | HTTP | Bytes | Audio | Delivery | Fetch seconds |
|---|---|---|---|---|---|---|
| Turn 3, the reassuring physician turn | pa-IN | 200 | 254,163 | 15.9 s | `[reassuringly]`, stability 0.6 (0.5 plus 0.1 for high certainty) | 8.3 |
| Turn 2, the worried patient turn | en-CA | 200 | 140,060 | 8.8 s | `[concerned]`, stability 0.6 | 3.2 |
| The closing check | pa-IN | 200 | 102,861 | 6.4 s | `[warmly]`, stability 0.5 | 3.7 |
| The closing check | en-CA | 404 | - | - | never spoken, only shown (CDR-008) | 0.0 |
| The `not_understood` line (second, model-free run on a fresh server) | en-CA | 200 | 81,128 | 5.1 s | `[warmly]`, stability 0.5 | 2.1 |
| The `not_understood` line | pa-IN | 404 | - | - | spoken to the physician only | 0.0 |

Fetch seconds are to the last byte, not to the first audio.
Nobody has listened to the clips yet; whether `[reassuringly]` sounds reassuring in Punjabi is for the listening test.

### Verdict

Matched IDR-005:

- Manner is read in the translate call with no extra model call: `warm` for the greeting, `reassuring` for the reassurance, `plain` for the alcohol question and the 911 instruction.
- Physician captions carry the manner; patient and companion captions never do.
- The reassuring turn is voiced `[reassuringly]` and the worried patient turn `[concerned]`, conveying the patient's worry to the physician rather than soothing it.
  Later listening found the voice did not carry these tags; since 16 November 2026 the voice is constant, and the worried turn would instead open with a phrase such as "Gurpreet Singh is asking, sounding worried, ..." (MDD-006, IDR-006).
- The frame took the adverb once, inside the frame ("ਕਹਿ ਰਹੇ ਹਨ, ਤਸੱਲੀ ਨਾਲ," / "is saying, reassuringly,"), and the tone check passed it.
  It is debatable whether the words alone ("Your heart tests were reassuring") already carried it, which IDR-005 says should leave the adverb out.

Matched CDR-008:

- `reassuranceLanded: true` on turn 4, after a worried turn 2 and a reassuring turn 3; `null` on every other turn.
- The alcohol question produced a `culture` cue; the greeting and the 911 instruction produced none.
- Signals reach every role, are relayed to the physician in English only and are speakable there, and each brings an understanding cue to the controller.
- The companion turn is accepted in Punjabi, framed as the companion, carries its emotion, and brings no nudge or cue.
- Nothing private reached the screen or the patient's device.

Did not match, or needs a look:

- The culture cue on turn 3 is cut mid-sentence at 200 characters, ending "so she is not at the same risk " with a trailing space: the model wrote more than the 200 characters it was asked for, and `_cue` in `server/trust.py` cuts with `text[:TRUST_CUE_MAX]`, with no word boundary and no trim.
- The same cue calls the patient "she" and "her", though the patient is Mr Singh and the relays use "they"; the culture prompt says nothing about gender.
  It is also clinical phrasing advice rather than a cultural sensitivity, which the culture prompt does not ask for.
- Turn 2's relay adds "you think" ("whether you think they will also have a heart attack"), which the patient did not say; the back-translation drops it again, so the check cannot see it.
- Turn 3's relay frames only its first sentence; the rest is direct speech, with "we have found this early" in the first person, as in the earlier runs.
- The 911 instruction is `plain`, not `urgent`; as a conditional safety instruction rather than a call to act now, that reading fits IDR-005, but the speakers may want it said more firmly.
