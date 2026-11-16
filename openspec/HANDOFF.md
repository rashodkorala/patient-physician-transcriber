# Session handoff, 16 November 2026

This note records the state of work at the end of an orchestration session, so the next agent can continue.
It is a snapshot, not a specification: the task files and decision records remain the source of truth.
Delete this file once everything in it has been merged, recorded in the task files, or dropped.

## How this session worked

- The supervising session only orchestrates, reviews, and decides.
- Coding agents run on Opus, document and research agents on Sonnet, and Fable is never used as a sub-agent.
- Each coding agent has its own worktree, its own files, and its own port pair.
- No coding agent edits any `tasks.md`, record, or document outside its grant; it reports a suggested task note instead, and one document pass writes them all at the end.
- Nothing has been pushed, and no pull request has been opened.

## Branch state

| Branch | Tip when written | Contents | State |
|---|---|---|---|
| `claude/ai-transcription-patient-physician-x8esrb` | `51c99dc` | Main branch | Untouched this session |
| `affect-in-words` (main checkout) | `ce713da` | The affect-in-words change, built, reviewed, fixed, and live-tested | Complete locally; a fix agent may add commits on top (see below) |
| `worktree-agent-a31b0aa63c185016d` | `6b8dec4` | Agent A, critical values | In progress, nothing committed yet |
| `worktree-agent-a9347e47d46ae04bc` | `6b8dec4` | Agent B, replay mode | In progress, nothing committed yet |
| `worktree-agent-a85389315b5d989fd` | `6895d8d` | Agent C, dose-changing summary fixture | In progress, one commit |
| `worktree-agent-a4a5e4bd3a7033c7c` | `6b8dec4` | Agent D, TV layout polish | In progress, nothing committed yet |
| `worktree-agent-a0f0a5b70b4728fc9` | `97c54d3` | Four commits from 10 November that never reached main | Keep until Agent C's branch is verified to contain them |

The worktrees are under `.claude/worktrees/agent-<id>/`.
If the session ended while agents were running, a worktree may hold uncommitted work: run `git status` in each before deciding anything, and never discard it unread.
All four wave 1 branches are based on `6b8dec4`, which is an ancestor of `affect-in-words`.

## Done: the affect-in-words change

The project lead decided that tone variation in the ElevenLabs voice does not work, so affect is carried in words.
MDD-006 and IDR-006 record this, and both were accepted by rashodkorala on 16 November 2026 with four answers recorded in their Review Notes.
MDD-005, IDR-005, and ADR-010 are amended by reference, not superseded.
ADR-011 and CDR-007 were extended to the change at his request.

What is built on `affect-in-words`:

- One constant voice delivery for every turn and every interpreter line.
- A patient or companion turn that is not calm carries exactly one hedged phrase in the reporting frame of the relay to the physician, for example "The patient says, sounding worried, that ...".
- No phrase on a physician turn, on a calm turn, or when the relay goes to the patient.
- The phrase is reported by the model, checked in code by `frame_problem` in `server/graph/turn_graph.py`, and removed from the note and summary sources.
- No new wire field; manner and emotion labels still reach the controller only.
- `docs/known-gaps.md` records the gaps: affect from words only, hosted APIs and not owned models, a voice that is not expressive.

Verified on that branch: 573 server tests, ruff, web lint, typecheck, contracts, 41 web unit tests, 21 end-to-end runs on the fake-model stack, `check_tdr.py`, and `openspec validate affect-in-words`.
Open tasks in the change: 5.3 (update the `manner-in-relay` Purpose on sync or archive) and 7.1 (deferred speaker review).

## Done: the live-model run

Recorded in `docs/voice-test.md`, section "Affect in words run, 16 November 2026" (commit `ce713da`).
Twenty-three typed turns in Tamil and Punjabi ran against the real model.
The phrase was correct on every turn, and nothing leaked into the note or summary.
The checks around it failed on faithful turns; the findings are listed in that section.

Not tested: spoken audio, real speech recognition, French, and native-speaker judgement.

## In progress when this was written

### Fix agent for the live-run findings (main checkout, `affect-in-words`, port 8620)

It is fixing five items in `server/graph/turn_graph.py`, `server/chains/note.py`, and `server/chains/summary.py`, as task group 9 of the affect-in-words change:

- A feeling the patient states in their own words is treated as an added phrase, which caused a false escalation.
- "Sounding confused" is allowed before a plainly stated dose.
- Back-translations come back in the wrong language, so the tone check compares nothing.
- Source-script text is pasted into an English relay after a retry hint.
- Gender is guessed from a name in a relay and in the clinical note.

It was told to re-run the failing turns live with at most 40 model calls and no ElevenLabs calls.
If group 9 is absent from `openspec/changes/affect-in-words/tasks.md`, this work did not land and must be redone from the findings in `docs/voice-test.md`.

### Wave 1 (four Opus agents in worktrees)

| Agent | Task | Owns | Ports | Brief in one line |
|---|---|---|---|---|
| A | mediator-voice 2.3, demo-night-mvp 6.3 | `server/critical_values.py`, its tests, new language data modules | 8630, 3630 | Number and unit words in Punjabi, Tamil, and Sinhala; Sinhala is absent today |
| B | demo-night-mvp 4.1 | Server recording and replay, replay controls on `/control`, `web/e2e/replay.mjs` | 8640, 3640 | Replay mode per TDM-001, proven with the network blocked |
| C | demo-night-mvp 3.7 | `server/fake_model.py`, summary tests, `web/e2e/summary*.mjs` | 8650, 3650 | A test-only fixture that changes a summary dose, proven refused in the browser |
| D | demo-night-mvp 4.2, TV half | `/screen` and its components, a new layout check | 8660, 3660 | Layout polish at 1080p and 4K in every state and language |

Agent A was also sent three failures from the live run to cover: "daily" against "every morning", Tamil number words with the "-ஓ" suffix, and a retry hint that quotes the source-script token.
Agent C was told to build on commit `ee0b614` from the stray branch and to bring across `3954c9c`, `7d5d6ae`, and `97c54d3`.

## Next steps, in order

1. Check each worktree for committed and uncommitted work, and finish or restart any agent that stopped part way.
2. Get an independent Opus review of each wave 1 branch before merging; the review of affect-in-words found six real gaps that passing tests had hidden.
3. Merge into one integration branch in the order A, C, D, B, and re-run the full suite and every end-to-end script after each merge.
4. Wave 2, after B is merged: controller keyboard shortcuts (demo-night-mvp 4.2) and speech start in the latency CSV (mediator-voice 3.5), both on `/control`.
5. Wave 3, one Sonnet document pass:
   - Write each agent's suggested notes into the task files.
   - Tick demo-night-mvp 0.6: ADR-011, CDR-005, CDR-006, CDR-007, and TDM-005 were accepted on 9 November (commits `8820908` and `1390fde`).
   - Correct demo-night-mvp 6.3, which still says Tamil is missing from the critical value check.
   - Note on demo-night-mvp 2.2 that the E5 model is cached locally and `tests/test_kb.py` passes with it.
   - Correct the mediator-voice tasks that still name OpenAI voices and ADR-009, and task 3.2, which describes voice tables that no longer exist.
   - Fill `implementation_refs` and `test_refs` in the 31 records that have none (demo-night-mvp 4.5).
   - Bring the related-changes column of `openspec/tdr/index.md` back in line with the records.
   - Archive `orb-speaking-state` once its six records have refs and its delta spec is synced.
6. Open a pull request for `affect-in-words` only when the project lead asks.

## Waiting on the project lead

- **Two wording refinements to the affect phrase**, which change what MDD-006 says, so they need his verdict before anyone builds them:
  skip the phrase when the patient's own words already state the feeling, and add "sounding frightened".
  The supervising session recommended both.
- **ElevenLabs credits are exhausted.**
  No audio could be produced, nobody has heard the phrase in the voice, and the app would fall back to Azure.
- **Latency is over target.**
  The live median was 5.0 seconds, and 4.2 seconds for turns that passed first time, against a goal of 3 seconds, before recognition and audio.
  No work has started on this.
- **TDM-001 expires on 20 November 2026.**
  Replay mode is being built, but the backup video depends on rehearsal 2.
- **ADR-008** is still proposed, which blocks every group of `add-multilingual-medical-consultation`.
- **`web/.next`** in the main checkout holds a build pointed at port 8620; rebuild before `next start`.

## Practical notes for the next agent

- Keys: `server/.env` holds the Anthropic and Azure keys, and the repo-root `.env.local` holds the ElevenLabs key; `scripts/dev.sh` loads both.
- Never print or copy key values.
- Ports 3000 and 8000 belong to the project lead; check a port is free before use and stop only your own processes.
- End-to-end scripts need `CHROMIUM_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"`.
- A fresh worktree needs `uv sync` in `server/`, and `npm ci` and `npx next typegen .` in `web/`.
- Run `python3 scripts/check_tdr.py` before each task group and each commit.
- Only the project lead decides a record's status; record a verdict only when he gives it explicitly.
