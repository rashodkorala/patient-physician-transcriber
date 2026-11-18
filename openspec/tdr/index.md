# Decision Registry

All Technical Decision Records (TDRs) for this project. `scripts/check_tdr.py` checks that this table matches the records on disk.

Only a human decides a status; an agent may record an explicit human verdict (EDR-001 rule 7). Proposed records are the human review queue.

| ID | Title | Type | Status | Owner | Related changes |
|---|---|---|---|---|---|
| [MDD-001](mdd/mdd-001-product-ai-medical-interpreter.md) | Product: AI medical interpreter with a verified record, Canada first | MDD | accepted | rashodkorala | add-multilingual-medical-consultation, demo-night-mvp |
| [MDD-002](mdd/mdd-002-methodology-spec-and-decision-driven.md) | Methodology: spec-driven (OpenSpec) plus decision-driven (DDSE) with human gates | MDD | accepted | rashodkorala | add-multilingual-medical-consultation, demo-night-mvp |
| [MDD-003](mdd/mdd-003-demo-night-scope.md) | Demo night scope: nine-beat script with Punjabi and French pairs | MDD | accepted | rashodkorala | demo-night-mvp |
| [MDD-004](mdd/mdd-004-mediator-voice.md) | Mediator voice: the interpreter speaks as a person between the parties, in reported speech | MDD | accepted | rashodkorala | affect-in-words, mediator-voice, trust-across-the-barrier |
| [MDD-005](mdd/mdd-005-trust-across-the-barrier.md) | Trust across the barrier: the patient has a voice, the physician's manner is carried, and the physician sees how it is landing | MDD | accepted | rashodkorala | affect-in-words, trust-across-the-barrier |
| [MDD-006](mdd/mdd-006-affect-in-words.md) | Affect in words: a constant interpreter voice, with the patient's affect carried as one hedged phrase in the reporting frame | MDD | accepted | rashodkorala | affect-in-words |
| [ADR-001](adr/adr-001-system-architecture.md) | Architecture: Python FastAPI server, Next.js front end, shared TV screen client | ADR | accepted | rashodkorala | demo-night-mvp, mediator-voice, trust-across-the-barrier |
| [ADR-002](adr/adr-002-knowledge-base-for-translation.md) | Knowledge base feeding translation: glossary, tone and culture, empathy, condition explainers | ADR | accepted | rashodkorala | demo-night-mvp, mediator-voice, trust-across-the-barrier |
| [ADR-003](adr/adr-003-human-interpreter-escalation.md) | Human interpreter escalation on low confidence and high-risk moments | ADR | accepted | rashodkorala | add-multilingual-medical-consultation, demo-night-mvp, mediator-voice, trust-across-the-barrier |
| [ADR-004](adr/adr-004-langgraph-turn-graph.md) | LangGraph for the per-turn translation graph; plain LangChain for single-pass chains | ADR | accepted | rashodkorala | affect-in-words, demo-night-mvp, mediator-voice, trust-across-the-barrier |
| [ADR-005](adr/adr-005-speech-provider.md) | Speech: Azure Speech primary, Google Speech backup | ADR | accepted | rashodkorala | demo-night-mvp, mediator-voice, trust-across-the-barrier |
| [ADR-006](adr/adr-006-llm-models.md) | LLM: Claude Sonnet 5.5 for live turns, Opus 5.5 for note and summary | ADR | accepted | rashodkorala | affect-in-words, demo-night-mvp, mediator-voice, trust-across-the-barrier |
| [ADR-007](adr/adr-007-in-memory-state-websocket.md) | In-memory visit state with WebSocket updates; no database for the demo | ADR | accepted | rashodkorala | demo-night-mvp, mediator-voice, trust-across-the-barrier |
| [ADR-008](adr/adr-008-automatic-high-risk-detection.md) | Automatic high-risk moment detection: suggest only | ADR | proposed | rashodkorala | add-multilingual-medical-consultation |
| [ADR-009](archived/adr-009-openai-voice-output.md) | Voice output: OpenAI text-to-speech with tone instructions; Azure keeps recognition | ADR | superseded | rashodkorala | mediator-voice |
| [ADR-010](adr/adr-010-elevenlabs-voice-output.md) | Voice output: ElevenLabs Eleven v4 replaces OpenAI text-to-speech; Azure stays fallback | ADR | accepted | rashodkorala | affect-in-words, mediator-voice, trust-across-the-barrier |
| [ADR-011](adr/adr-011-grounded-generation-checked-by-code.md) | Explain-back, note, and summary: frozen sources, model proposes, code checks provenance and values | ADR | accepted | rashodkorala | affect-in-words, demo-night-mvp, trust-across-the-barrier |
| [ADR-012](adr/adr-012-clinic-design-system.md) | Interface: a clinic design system, light, legible at three metres, one hyperlegible typeface, meaning-only colour | ADR | accepted | rashodkorala | trust-across-the-barrier |
| [CDR-001](cdr/cdr-001-visit-websocket-events.md) | Visit WebSocket event contract | CDR | accepted | rashodkorala | demo-night-mvp, mediator-voice, trust-across-the-barrier |
| [CDR-002](cdr/cdr-002-turn-result-schema.md) | Turn result schema | CDR | accepted | rashodkorala | affect-in-words, demo-night-mvp, mediator-voice, trust-across-the-barrier |
| [CDR-003](cdr/cdr-003-names-and-interpreter-lines.md) | Participant names and interpreter lines on the visit channel | CDR | accepted | rashodkorala | mediator-voice, trust-across-the-barrier |
| [CDR-004](cdr/cdr-004-interpreter-voice-playback-events.md) | Interpreter voice playback on the visit channel | CDR | accepted | rashodkorala | orb-speaking-state, trust-across-the-barrier |
| [CDR-005](cdr/cdr-005-consent-and-explain-back-events.md) | Consent and explain-back on the visit channel | CDR | accepted | rashodkorala | demo-night-mvp, trust-across-the-barrier |
| [CDR-006](cdr/cdr-006-record-entries-review-corrections-and-tamper.md) | Record chain entries, review corrections, interpreter dismissal, and presenter controls | CDR | accepted | rashodkorala | demo-night-mvp, trust-across-the-barrier |
| [CDR-007](cdr/cdr-007-clinical-note-and-patient-summary.md) | Clinical note with provenance and patient summary on the visit channel | CDR | accepted | rashodkorala | affect-in-words, demo-night-mvp, trust-across-the-barrier |
| [CDR-008](cdr/cdr-008-patient-voice-manner-and-trust-events.md) | Patient signals, manner, trust updates, companion turns, and the closing check on the visit channel | CDR | accepted | rashodkorala | affect-in-words, trust-across-the-barrier |
| [CDR-009](cdr/cdr-009-patient-transcript-review.md) | Patient confirmation of a captured transcript before translation | CDR | accepted | rashodkorala | demo-night-mvp |
| [EDR-001](edr/edr-001-agent-working-rules.md) | Agent working rules: TDR gates, annotations, commits, and reviews | EDR | accepted | rashodkorala | add-multilingual-medical-consultation, demo-night-mvp |
| [EDR-002](edr/edr-002-testing-strategy.md) | Testing: pytest with mocked LLM, speaker-rated tone set, latency check | EDR | accepted | rashodkorala | affect-in-words, demo-night-mvp, mediator-voice, trust-across-the-barrier |
| [IDR-001](idr/idr-001-push-to-talk-turns.md) | Push-to-talk per speaker instead of diarisation | IDR | accepted | rashodkorala | demo-night-mvp, mediator-voice, trust-across-the-barrier |
| [IDR-002](idr/idr-002-kb-retrieval-chroma.md) | Chroma with local multilingual embeddings plus exact-match glossary lookup | IDR | accepted | rashodkorala | demo-night-mvp |
| [IDR-003](idr/idr-003-hash-chain-integrity.md) | SHA-256 hash chain for the record-verified badge | IDR | accepted | rashodkorala | demo-night-mvp, trust-across-the-barrier |
| [IDR-004](idr/idr-004-continuous-listening-by-language.md) | Hands-free continuous listening, with the speaker found by spoken language | IDR | accepted | rashodkorala | continuous-listening, trust-across-the-barrier |
| [IDR-005](idr/idr-005-manner-vocabulary-and-voice-delivery.md) | Manner: an eight-word vocabulary read from the words, carried into the voice, the frame, and the caption label | IDR | accepted | rashodkorala | affect-in-words, trust-across-the-barrier |
| [IDR-006](idr/idr-006-affect-phrase-in-the-frame-and-constant-voice.md) | Affect phrase in the reporting frame, and one constant voice delivery | IDR | accepted | rashodkorala | affect-in-words |
| [IDR-007](idr/idr-007-remove-model-tone-check.md) | Remove the separate model tone check for demo turns | IDR | accepted | rashodkorala | demo-night-mvp, affect-in-words |
| [IDR-008](idr/idr-008-review-low-confidence-speech.md) | Physician review of low-confidence speech before submission | IDR | accepted | rashodkorala | demo-night-mvp |
| [TDM-001](tdm/tdm-001-replay-mode-safety-net.md) | Replay mode and backup video as demo safety net | TDM | accepted | rashodkorala | demo-night-mvp |
| [TDM-002](tdm/tdm-002-presenter-mismatch-control.md) | Presenter mismatch control for the blocked-dose beat | TDM | accepted | rashodkorala | demo-night-mvp |
| [TDM-003](tdm/tdm-003-sinhala-tamil-test-languages.md) | Sinhala and Tamil as test-only languages before demo night | TDM | accepted | rashodkorala | demo-night-mvp |
| [TDM-004](tdm/tdm-004-tamil-live-language.md) | Tamil is the chosen live language, alongside Punjabi and French, spoken by ElevenLabs | TDM | accepted | rashodkorala | demo-night-mvp, mediator-voice |
| [TDM-005](tdm/tdm-005-hidden-record-tamper-control.md) | Hidden record-tamper control for the demo | TDM | accepted | rashodkorala | demo-night-mvp |

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
