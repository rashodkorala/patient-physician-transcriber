# Patient-Physician Transcriber

A demo prototype for a patient and physician who speak different languages.
It captures one speaker at a time, shows the original and interpreted text on a shared screen, and reads the interpretation aloud.
The patient can ask for clarification in their own language, and the physician can check medication values before the relay plays.

The demo uses fictional consultations.
The [English and Canadian French demo script](docs/demo-night-english-french-voice-script.md) has voice lines and cues for each screen.

## What you can try

| Feature | What the demo shows |
| --- | --- |
| Bilingual conversation | Push-to-talk for physician, patient, and companion, with speaker labels, side-by-side captions, and spoken interpretation. |
| Consent and pause | The patient can accept the notice in their language, pause the visit, and resume from their own device. |
| Transcript review | A low-confidence push-to-talk capture can be reviewed on the physician screen before translation. For patient speech, the patient can privately confirm what they said or choose to repeat it. |
| Patient controls | The patient can ask for a simpler explanation, slower speech, or a repeat. The physician sees the request during the visit. |
| Medication checks | The app compares detected critical values before release. It holds back a mismatch and asks the physician to confirm a matching medication instruction when read-back is required. The Presenter controls can simulate a mismatch. |
| Human interpreter | Either participant can request an interpreter. The connection is simulated in the demo. |
| Explain-back and review | The physician can ask the patient to explain the plan in their own words. The patient can review or correct settled transcript entries, with the original retained in the visit history. |
| Visit outputs | The app can generate a physician note with source links and a patient-language summary. The record badge reflects the integrity of the current visit’s hash chain. |

English is the physician language.
Canadian French, Punjabi, and Tamil are selectable patient languages.
Sinhala is available in test mode, and other listed languages are roadmap entries.
Language availability and rehearsal evidence are tracked in the [speech test log](docs/speech-test.md).

## Where it needs more tuning

- **Recognition and confidence.** Correct-looking captures and translations can still fall below the 0.70 cutoff. The app currently displays a combined score, so an operator may have to infer whether recognition or translation was the limiting factor. Separating those scores and testing with native speakers would make the demo easier to diagnose.
- **Latency.** Recent French rehearsals saw roughly two to three seconds of server processing on many first-pass turns and around five seconds for some retries. Microphone recognition and audio playback add time. Ordinary demo turns now skip the separate model tone-check call. Test end-to-end timing on the actual demo setup.
- **Voice and wording.** The interpreter uses steady voice settings and carries cues such as worry in words inferred from the transcript. The French phrasing, pronunciation, interruptions, and audio recovery still need listening tests with native speakers.
- **Recorded inputs.** The solo demo can play prerecorded dialogue into the microphone. Direct audio-file input and offline replay remain open.
- **Clinical and deployment readiness.** The prototype needs broader translation and medication validation, a production interpreter integration, access controls, durable records, and a privacy and deployment review. Visit state is in memory and clears on backend restart. Use fictional content on a trusted demo network.

See the [known gaps](docs/known-gaps.md) and the [parked product roadmap](openspec/changes/add-multilingual-medical-consultation) for detail.

## Run locally

You’ll need Python 3.12 or newer, [uv](https://docs.astral.sh/uv/), Node.js 22 or newer, and Chrome for microphone capture.

```bash
cp server/.env.example server/.env
(cd server && uv sync && uv run python scripts/download_model.py)
(cd web && npm ci)
```

Set `ANTHROPIC_API_KEY`, `AZURE_SPEECH_KEY`, and `AZURE_SPEECH_REGION` in `server/.env`.
For ElevenLabs playback, set `ELEVENLABS_API_KEY` in the root `.env.local` or in `server/.env`.
Azure also supplies fallback playback.
The first run downloads the multilingual embedding model.

```bash
(cd server && uv run python scripts/check_keys.py)
scripts/dev.sh --prod
```

Use `scripts/dev.sh` without `--prod` for development.
The startup log identifies the translator, recognition provider, voice, and embedding model.

| View | URL |
| --- | --- |
| Physician controls | `http://localhost:3000/control` |
| Shared display | `http://<laptop-ip>:3000/screen` |
| Patient phone or tablet | `http://<laptop-ip>:3000/patient` |
| Physician record | `http://localhost:3000/record` |

Put the demo devices on the same Wi-Fi.
Use the laptop address printed by the startup script for the TV and patient device.
On the physician screen, choose the patient language, show the consent notice, and wait for consent before using the speaking controls.

For a credential-free smoke test, run `TRANSLATOR=fake EMBEDDINGS=hashing scripts/dev.sh --prod` without live service keys and enter a typed turn.
Fake translation echoes the input with a language marker and can exercise the app flow without a live translation.

## Development and verification

```bash
python3 scripts/check_tdr.py
(cd server && uv run ruff check . && uv run ruff format --check . && uv run pytest)
(cd web && npm run lint && npm test && npm run check:contracts && npm run build)
```

The Next.js frontend communicates with a FastAPI backend over a role-filtered WebSocket.
The backend uses a LangGraph turn pipeline for translation and deterministic checks.
See [AGENTS.md](AGENTS.md) for the OpenSpec workflow, the [decision registry](openspec/tdr/index.md) for accepted and proposed decisions, and [web/e2e](web/e2e) for Chromium rehearsals and regressions.
