# Decision Layer (DDSE)

This folder holds the project's **Technical Decision Records (TDRs)**, following [Decision-Driven Software Engineering (DDSE) v1.1](https://github.com/ddse-foundation/ddse-foundation). OpenSpec (in `openspec/specs` and `openspec/changes`) says **what** the system must do. TDRs say **why** it is built this way and **which** choices are allowed. Humans make decisions; AI agents implement within them.

Registry: [`index.md`](index.md). Templates: [`templates/`](templates/). Agent rules: [`EDR-001`](edr/edr-001-agent-working-rules.md) and [`AGENTS.md`](../../AGENTS.md).

## Record types

| Type | Name | Use it for | Approver |
|---|---|---|---|
| MDD | Major Design Decision | Product, strategy, methodology, scope | Project lead |
| ADR | Architectural Decision Record | System structure, major components, vendors | Project lead |
| CDR | Contract Decision Record | Every boundary between components (events, APIs, schemas) | Project lead plus front-end and back-end owners |
| EDR | Engineering Decision Record | Practices: testing, workflow, tooling | One other team member |
| IDR | Implementation Decision Record | Component-level choices: algorithms, libraries, patterns | One other team member |
| TDM | Technical Decision Memo | Temporary or experimental choices with an expiry date | Self-approved with notification |

Hierarchy: MDD, then ADR, then CDR, EDR, and IDR. A child record lists its parents in `related_decisions`. When a parent changes, review its children.

## Lifecycle

```
 Decision Required --> Decision In Progress --> Decision Approved --> Implementation
 (anyone spots a       (record drafted,         (a HUMAN sets         (/opsx:apply; code
  choice to make)       status: proposed)        status: accepted)     cites the record)

 proposed --> accepted --> superseded (moved to archived/) or deprecated
          \-> rejected
```

- Agents may draft records (`proposed_by: agent`) but never set `accepted`.
- A task in an OpenSpec change may start only when every TDR listed for its task group is `accepted`.
- Superseded records move to `archived/` and the new record lists them in `related_decisions`.
- A TDM lapses on its `expires` date unless renewed or promoted to another type.

## Naming and format

- File: `{type}-{NNN}-{kebab-title}.md`, three-digit numbers, sequential per type, never reused.
- Ids are lowercase in files and front matter (`adr-004`) and uppercase in prose, code, and commits (`ADR-004`).
- Front matter fields: `id`, `title`, `status`, `date`, `authors`, `reviewers`, `decision_owner`, `proposed_by`, `category`, `related_decisions`, `related_specs`, `related_changes`, `ai_context` (`implementation_priorities`, `framework_hints`, `validation_rules`), `affects`, `implementation_refs`, `test_refs`, and `expires` for TDMs.
- Required sections: Summary, Context, Decision, Alternatives Considered, Consequences, Implementation. CDRs also need Contract Specification, Data Schemas, Evolution Strategy, and Testing Requirements.

## Traceability

- Code: `@implements ADR-004: LangGraph turn graph`, `@contract ws:/ws/visit` for CDR-governed code, `@see openspec/tdr/adr/adr-004-langgraph-turn-graph.md`.
- Tests: name the record they verify (for example `test_turn_result_schema_cdr_002`).
- Commits: `feat: live turn graph (ADR-004, CDR-002)`.
- After implementation, fill `implementation_refs` and `test_refs` in the record.

## Checking

```bash
python3 scripts/check_tdr.py            # validate records, index, references; show review queue
python3 scripts/check_tdr.py --json     # same, machine readable
```

## Notes on DDSE alignment

We follow DDSE v1.1 (six types, `tdr/` layout with `archived/` and `index.md`, `ai_context` in front matter, `@implements` annotations). Two local choices: the folder lives inside `openspec/` so specs and decisions sit together, and we add `proposed_by`, `related_specs`, and `related_changes` to link records to OpenSpec. The upstream DDSE validator does not yet match v1.1, so we use `scripts/check_tdr.py`.
