# Patient-Physician Transcriber

A trust-first AI transcription product for medical consultations. The patient and the physician can both see who said what, verify their own words, and check that the record has not been altered.

- Market research and baseline choice (Abridge): [`docs/product-research.md`](docs/product-research.md)
- Project context and constraints: [`openspec/config.yaml`](openspec/config.yaml)
- First change under review: [`openspec/changes/add-trust-first-transcription`](openspec/changes/add-trust-first-transcription)

## Core capabilities

| Capability | What it guarantees |
|---|---|
| `consent-management` | Per-visit, granular, revocable consent; off-the-record pause; retention notice |
| `speaker-attributed-transcription` | Every segment labelled patient, physician, companion, or unknown, with confidence |
| `patient-verification` | Patient confirms or corrects their words; physician signs off; originals preserved |
| `note-provenance` | Every note sentence linked to its source and tagged as stated or AI inference |
| `audit-integrity` | Hash-chained audit trail, verifiable copies, patient-visible access log |
| `tone-coaching` | Private, opt-in, post-visit communication feedback for physicians |
| `patient-summary` | Plain-language summary in the patient's language with a "questions answered" list |

## Spec-driven workflow (OpenSpec)

This project uses [OpenSpec](https://github.com/Fission-AI/OpenSpec). No code is written until its spec is agreed.

```bash
npx @fission-ai/openspec@1.14.3 list                 # changes in flight
npx @fission-ai/openspec@1.14.3 show <change>        # read a change
npx @fission-ai/openspec@1.14.3 validate <change> --strict
```

In Claude Code:
- `/opsx:propose "<idea>"` creates a new change (proposal, specs, design, tasks).
- `/opsx:apply` implements the tasks of an agreed change.
- `/opsx:archive` merges the change's specs into `openspec/specs/` once shipped.
