# CLAUDE.md

Follow [`AGENTS.md`](AGENTS.md). In short:

- Behaviour lives in OpenSpec (`openspec/changes/`, `openspec/specs/`); use the `/opsx:*` commands.
- Decisions live in DDSE records (`openspec/tdr/`, registry `openspec/tdr/index.md`, guide `openspec/tdr/README.md`).
- Rules for artifacts and for apply and archive are in `openspec/config.yaml`.
- Run `python3 scripts/check_tdr.py` before implementing a task group and before every commit. Never implement against a proposed TDR, and never decide a TDR status yourself; only record a verdict a named human gave explicitly and asked you to record (EDR-001 rule 7).
- Annotate code with `@implements <TDR-ID>: <title>` and cite TDR ids in commit messages.
- Write in UK English with the Oxford comma and no em-dashes.
