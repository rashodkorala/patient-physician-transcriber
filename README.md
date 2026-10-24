# Patient-Physician Transcriber

An AI medical interpreter with a verified record, built first for Canada. A patient and a physician who do not share a language see their conversation live in both languages on a shared in-room screen, hear each translation spoken aloud, and can call in a human interpreter at any time. Afterwards, both verify the bilingual record in their own language.

- Market research, language data, and baseline choices: [`docs/product-research.md`](docs/product-research.md)
- Project context and constraints: [`openspec/config.yaml`](openspec/config.yaml)
- Product roadmap change: [`openspec/changes/add-multilingual-medical-consultation`](openspec/changes/add-multilingual-medical-consultation)
- Demo night (19 November 2026) change: [`openspec/changes/demo-night-mvp`](openspec/changes/demo-night-mvp)
- Decision registry: [`openspec/tdr/index.md`](openspec/tdr/index.md)

First-version languages: English, French, Mandarin, Cantonese, Punjabi, Urdu, Arabic, Farsi, Tagalog, Spanish, Portuguese, Sinhala, and Tamil.

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
(cd server && uv sync) && (cd web && npm install)
scripts/dev.sh            # development
scripts/dev.sh --prod     # production build, for rehearsals and demo night
```

- Physician laptop: `http://localhost:3000/control`
- TV: `http://<laptop-ip>:3000/screen` (same network)
- Without keys, `TRANSLATOR=fake` echoes text with a language tag and nothing is spoken; use the typed turn box.

Tests: `cd server && uv run pytest`, `cd web && npm run check:contracts && npm run build`.

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
