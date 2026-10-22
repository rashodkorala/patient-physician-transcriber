# Decision Registry

All Technical Decision Records (TDRs) for this project. `scripts/check_tdr.py` checks that this table matches the records on disk.

Only a human decides a status; an agent may record an explicit human verdict (EDR-001 rule 7). Proposed records are the human review queue.

| ID | Title | Type | Status | Owner | Related changes |
|---|---|---|---|---|---|
| [MDD-001](mdd/mdd-001-product-ai-medical-interpreter.md) | Product: AI medical interpreter with a verified record, Canada first | MDD | accepted | rashodkorala | add-multilingual-medical-consultation, demo-night-mvp |
| [MDD-002](mdd/mdd-002-methodology-spec-and-decision-driven.md) | Methodology: spec-driven (OpenSpec) plus decision-driven (DDSE) with human gates | MDD | accepted | rashodkorala | add-multilingual-medical-consultation, demo-night-mvp |
| [MDD-003](mdd/mdd-003-demo-night-scope.md) | Demo night scope: nine-beat script with Punjabi and French pairs | MDD | accepted | rashodkorala | demo-night-mvp |
| [ADR-001](adr/adr-001-system-architecture.md) | Architecture: Python FastAPI server, Next.js front end, shared TV screen client | ADR | accepted | rashodkorala | demo-night-mvp |
| [ADR-002](adr/adr-002-knowledge-base-for-translation.md) | Knowledge base feeding translation: glossary, tone and culture, empathy, condition explainers | ADR | accepted | rashodkorala | demo-night-mvp |
| [ADR-003](adr/adr-003-human-interpreter-escalation.md) | Human interpreter escalation on low confidence and high-risk moments | ADR | accepted | rashodkorala | add-multilingual-medical-consultation, demo-night-mvp |
| [ADR-004](adr/adr-004-langgraph-turn-graph.md) | LangGraph for the per-turn translation graph; plain LangChain for single-pass chains | ADR | accepted | rashodkorala | demo-night-mvp |
| [ADR-005](adr/adr-005-speech-provider.md) | Speech: Azure Speech primary, Google Speech backup | ADR | accepted | rashodkorala | demo-night-mvp |
| [ADR-006](adr/adr-006-llm-models.md) | LLM: Claude Sonnet 5.5 for live turns, Opus 5.5 for note and summary | ADR | accepted | rashodkorala | demo-night-mvp |
| [ADR-007](adr/adr-007-in-memory-state-websocket.md) | In-memory visit state with WebSocket updates; no database for the demo | ADR | accepted | rashodkorala | demo-night-mvp |
| [ADR-008](adr/adr-008-automatic-high-risk-detection.md) | Automatic high-risk moment detection: suggest only | ADR | proposed | rashodkorala | add-multilingual-medical-consultation |
| [CDR-001](cdr/cdr-001-visit-websocket-events.md) | Visit WebSocket event contract | CDR | accepted | rashodkorala | demo-night-mvp |
| [CDR-002](cdr/cdr-002-turn-result-schema.md) | Turn result schema | CDR | accepted | rashodkorala | demo-night-mvp |
| [EDR-001](edr/edr-001-agent-working-rules.md) | Agent working rules: TDR gates, annotations, commits, and reviews | EDR | accepted | rashodkorala | add-multilingual-medical-consultation, demo-night-mvp |
| [EDR-002](edr/edr-002-testing-strategy.md) | Testing: pytest with mocked LLM, speaker-rated tone set, latency check | EDR | accepted | rashodkorala | demo-night-mvp |
| [IDR-001](idr/idr-001-push-to-talk-turns.md) | Push-to-talk per speaker instead of diarisation | IDR | accepted | rashodkorala | demo-night-mvp |
| [IDR-002](idr/idr-002-kb-retrieval-chroma.md) | Chroma with local multilingual embeddings plus exact-match glossary lookup | IDR | accepted | rashodkorala | demo-night-mvp |
| [IDR-003](idr/idr-003-hash-chain-integrity.md) | SHA-256 hash chain for the record-verified badge | IDR | accepted | rashodkorala | demo-night-mvp |
| [TDM-001](tdm/tdm-001-replay-mode-safety-net.md) | Replay mode and backup video as demo safety net | TDM | accepted | rashodkorala | demo-night-mvp |

## Hierarchy

```
MDD-001 product ----+---- MDD-002 methodology ---- EDR-001 agent rules
                    |                                  EDR-002 testing
                    +---- MDD-003 demo scope
                              |
        +---------+-----------+-----------+
     ADR-001   ADR-002     ADR-003     ADR-007
     system    knowledge   escalation  state
        |      base           |           |
     ADR-005   IDR-002     ADR-004 <------+---- CDR-001 events
     speech    retrieval   LangGraph           CDR-002 turn result
     ADR-006                  |
     models                IDR-001 push-to-talk
                           IDR-003 hash chain
                           TDM-001 replay (expires 2026-11-20)
```
