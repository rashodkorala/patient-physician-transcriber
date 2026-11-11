# Patient-Physician Transcriber

An AI medical interpreter with a verified record, built first for Canada. A patient and a physician who do not share a language see their conversation live in both languages on a shared in-room screen, hear each translation spoken aloud, and can call in a human interpreter at any time. Afterwards, both verify the bilingual record in their own language.

- Market research, language data, and baseline choices: [`docs/product-research.md`](docs/product-research.md)
- Project context and constraints: [`openspec/config.yaml`](openspec/config.yaml)
- Product roadmap change: [`openspec/changes/add-multilingual-medical-consultation`](openspec/changes/add-multilingual-medical-consultation)
- Demo night (19 November 2026) change: [`openspec/changes/demo-night-mvp`](openspec/changes/demo-night-mvp)
- Decision registry: [`openspec/tdr/index.md`](openspec/tdr/index.md)

First-version languages: English, French, Mandarin, Cantonese, Punjabi, Urdu, Arabic, Farsi, Tagalog, Spanish, Portuguese, Sinhala, and Tamil.

## Trust across the barrier

Accurate words are not enough when two people share no language; what gets lost first is how something was said.
The interpreter therefore carries the physician's manner (warm, reassuring, gentle, serious, urgent, apologetic, or encouraging) into its voice, into the reporting frame when words alone would lose it, and into a label the patient can read in their own language.
The patient has their own controls during the visit, in their own language, so they can say they did not understand or ask for slower or repeated speech without needing permission or English.
The physician privately sees how the visit is landing: the patient's emotion turn by turn, whether a reassurance landed, every patient signal, and a cue when a topic is sensitive in the patient's culture.
A companion can speak as a labelled third speaker, and the interpreter can close the loop by asking the patient whether anything should be explained again.
Decisions: MDD-005, CDR-008, IDR-005; interface: ADR-012 (`web/design/README.md`).

## Core capabilities

| Capability | What it guarantees |
|---|---|
| `medical-interpretation` | Live two-way interpretation on a shared screen; glossary; read-back of doses; comprehension check; human interpreter hand-off |
| `consent-management` | Consent and retention notice in the patient's language; granular, revocable; off-the-record pause |
| `speaker-attributed-transcription` | Bilingual segments with speaker role, original text, translation, and confidence |
| `patient-verification` | Patient verifies in their own language via back-translation; physician signs off; originals preserved |
| `note-provenance` | Every note sentence linked to original speech and translation, tagged as stated or AI inference |
| `audit-integrity` | Hash-chained audit trail, verifiable copies, patient-visible access log |
| `communication-coaching` | Private, opt-in feedback on what was lost or misunderstood in translation |
| `patient-summary` | Plain-language summary in the patient's language, read aloud on request, with exact doses |

## How we work: spec-driven and decision-driven

AI agents build; humans decide and review.

| Layer | Answers | Lives in |
|---|---|---|
| Specs ([OpenSpec](https://github.com/Fission-AI/OpenSpec)) | What must the system do? | `openspec/specs/`, `openspec/changes/` |
| Decisions ([DDSE v1.1](https://github.com/ddse-foundation/ddse-foundation)) | Why is it built this way, and which choices are allowed? | `openspec/tdr/` (MDD, ADR, CDR, EDR, IDR, TDM) |
| Rules | How do the two bind together? | `openspec/config.yaml`, [`AGENTS.md`](AGENTS.md) |

```
 decision needed --> TDR drafted (proposed) --> HUMAN accepts --> change specs, design, tasks cite it
        --> agent implements (/opsx:apply, code carries @implements) --> HUMAN reviews PR --> archive
```

```bash
python3 scripts/check_tdr.py    # validate decisions and show the human review queue
```

## Run the demo

Requirements: Python 3.12+ with [uv](https://docs.astral.sh/uv/), Node 20+.

```bash
cp server/.env.example server/.env    # add ANTHROPIC_API_KEY and AZURE_SPEECH_KEY / AZURE_SPEECH_REGION
(cd server && uv sync && uv run python scripts/download_model.py) && (cd web && npm install)
scripts/dev.sh            # development
scripts/dev.sh --prod     # production build, for rehearsals and demo night
```

- Physician laptop: `http://localhost:3000/control`
- TV: `http://<laptop-ip>:3000/screen` (same network); `scripts/dev.sh` prints both URLs when it starts.
- Patient's tablet or phone: `http://<laptop-ip>:3000/patient` (same network): consent, the latest translation in the patient's language, their own controls during the visit (I did not understand, please speak more slowly, say that again, pause, a human interpreter), and the transcript and summary afterwards.
- Record view: `http://localhost:3000/record` (the physician's note with provenance).
- The server's first log lines say which translator and speech service the run uses; check for `Translator: Claude` before a live run.

### First run on a Mac

1. Install the tools: `brew install uv node`, and use Google Chrome for `/control`.
2. Copy `server/.env.example` to `server/.env` and fill in `ANTHROPIC_API_KEY`, `AZURE_SPEECH_KEY`, and `AZURE_SPEECH_REGION`; leave the other lines blank.
3. Run `uv sync` and `uv run python scripts/download_model.py` in `server/` (about 1 GB the first time), then `npm install` in `web/`.
4. Run `uv run python scripts/check_keys.py` in `server/`; it checks both keys, the Claude models, and the Azure voices, makes no paid calls, and never prints a key.
5. Run `scripts/dev.sh` from the repository root and open the two printed URLs.
6. Allow the microphone when Chrome asks, and allow incoming connections if macOS asks, so the TV can reach the laptop.
7. Put the TV (or any second screen) on the same Wi-Fi as the laptop.
- Without keys, `TRANSLATOR=fake` echoes text with a language tag, swaps in approved glossary terms, and speaks nothing; use the typed turn box.
- Where the embedding model cannot be downloaded, run the server with `EMBEDDINGS=hashing` and `uv sync --no-group embeddings`; retrieval then uses a test embedder and is not fit for rehearsals.

Checks before every commit:

```bash
(cd server && uv run ruff check . && uv run ruff format --check . && uv run pytest)
(cd web && npm run lint && npm run check:contracts && npm run build)
```

Browser checks against `scripts/dev.sh --prod` with `TRANSLATOR=fake`: `node web/e2e/week1.mjs` and `node web/e2e/week2.mjs [baseUrl] [screenshotDir]`, plus the scripts in `web/e2e/` for each later beat (read each script's header for its arguments).
The scripts drive Chromium through Playwright; on a Mac without a Playwright browser, set `CHROMIUM_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"`.
In typed turns the fake model treats `(test: mismatch)` as a dose it gets wrong twice (blocked) and `(test: tone)` as a failed tone check (escalated).

## OpenSpec commands

No code is written until its spec is agreed and its decisions are accepted.

```bash
npx @fission-ai/openspec@1.14.3 list                 # changes in flight
npx @fission-ai/openspec@1.14.3 show <change>        # read a change
npx @fission-ai/openspec@1.14.3 validate <change> --strict
```

In Claude Code:
- `/opsx:propose "<idea>"` creates a new change (proposal, specs, design, tasks).
- `/opsx:update` revises an existing change and keeps its artifacts coherent.
- `/opsx:apply` implements the tasks of an agreed change.
- `/opsx:archive` merges the change's specs into `openspec/specs/` once shipped.
