# Working on this repository (AI agents and humans)

This project is built with **spec-driven development** (OpenSpec) and **Decision-Driven Software Engineering** (DDSE v1.1). AI agents do most of the building; humans make the decisions and review the work.

- **What** the system must do: OpenSpec changes and specs in `openspec/changes/` and `openspec/specs/`.
- **Why and how** it is built: Technical Decision Records (TDRs) in `openspec/tdr/` (registry: `openspec/tdr/index.md`).
- **Rules** binding the two: `openspec/config.yaml` (`rules` and `operations`) and EDR-001.

## The loop

```
 idea --> /opsx:explore --> decision needed? --yes--> draft TDR (proposed) --> HUMAN accepts
                                   | no                                            |
                                   v                                               v
                        /opsx:propose: proposal, specs, design (cites TDRs), tasks (lists TDRs)
                                   |
                         HUMAN reviews the change
                                   |
          /opsx:apply: agent builds task groups whose TDRs are all accepted
                                   |
          new decision needed mid-task? --> draft proposed TDR, STOP, ask a human
                                   |
          PR (template checklist) --> HUMAN review and merge --> /opsx:archive
```

## Roles

| Who | Does | Never does |
|---|---|---|
| AI agent | Drafts proposals, specs, designs, tasks, and proposed TDRs; implements accepted work; writes tests; annotates code; records a human's explicit verdict when asked (EDR-001 rule 7) | Decides a TDR status on its own; implements against a proposed TDR; makes a silent architectural choice |
| Human (decision owner) | Accepts or rejects TDRs; reviews changes and pull requests; merges | Approves work whose TDRs are not accepted |

## What counts as a decision, and which record

| If the choice is about | Record type |
|---|---|
| Product direction, scope, methodology | MDD |
| System structure, major components, vendors, models | ADR |
| An interface between components (events, APIs, schemas) | CDR |
| How we work: tests, tooling, process | EDR |
| A component-level algorithm, library, or pattern | IDR |
| A temporary or experimental choice | TDM (with `expires`) |

## Decision scope

A TDR binds only the OpenSpec changes listed in its `related_changes`. When applying a change, treat as decided only the records that list it. Never carry another change's decisions over silently, and never re-decide them: a missing decision is drafted as a proposed TDR for this change and waits for a human. `add-multilingual-medical-consultation` is a parked roadmap; do not apply it. The only accepted records that bind it are MDD-001, MDD-002, ADR-003 (its escalation rules, not the demo-only simulated call), and EDR-001; all stack, vendor, state, and contract records are demo-only. It moves to product only if the demo works really well, by a human decision after demo night.

## Before you implement

1. Read `openspec/tdr/index.md`, then the records listed on the task group's `TDRs:` line, top down (MDD, ADR, CDR, EDR, IDR). Use each record's `ai_context`.
2. Run `python3 scripts/check_tdr.py`. If the task group appears under "blocked", stop and tell the human which TDRs need review.
3. Read the change's `specs/` for the behaviour and scenarios to satisfy.

## While implementing

- Annotate governed code:
  ```python
  # @implements ADR-004: LangGraph turn graph
  # @contract TurnResult (CDR-002)
  # @see openspec/tdr/adr/adr-004-langgraph-turn-graph.md
  ```
- Name tests after the record they verify, for example `test_turn_result_schema_cdr_002`.
- If you hit a choice no accepted TDR covers: copy the matching template from `openspec/tdr/templates/`, fill it with `status: proposed` and `proposed_by: agent`, add a row to `openspec/tdr/index.md`, and stop.
- Tick tasks in the change's `tasks.md` only when their verification passes.

## Commits and pull requests

- Commit messages cite TDR ids: `feat: live turn graph (ADR-004, CDR-002)`.
- Run `python3 scripts/check_tdr.py` and the project's tests before pushing.
- Open pull requests with `.github/pull_request_template.md` and wait for human review.

## Writing conventions

UK English, Oxford comma, no em-dashes. Specs describe behaviour only; vendor and library names belong in TDRs and design.
