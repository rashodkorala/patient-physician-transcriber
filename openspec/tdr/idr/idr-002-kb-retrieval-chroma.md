---
id: idr-002
title: "Chroma with local multilingual embeddings plus exact-match glossary lookup"
status: proposed
date: 2026-10-22
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: implementation
related_decisions: [adr-002, adr-004]
related_specs: []
related_changes: [demo-night-mvp]
ai_context:
  implementation_priorities:
    - "Glossary terms found by exact and fuzzy match first"
    - "Vector search for tone, empathy, and explainers"
  framework_hints:
    - "langchain-chroma, sentence-transformers intfloat/multilingual-e5-small"
    - "Index built at server start from server/kb/"
  validation_rules:
    - "Retrieval works offline"
    - "Glossary matches are deterministic"
affects: [server/kb/]
implementation_refs: []
test_refs: []
---

# IDR-002: Chroma with local multilingual embeddings plus exact-match glossary lookup

## Summary

Store the knowledge base in a local Chroma index with multilingual embeddings, and look up glossary terms by exact and fuzzy match.

## Context

- **Feature or component**: retrieve node of the turn graph.
- **Technical requirements**: fast, offline, multilingual.
- **Constraints**: small content set.

## Decision

Build the Chroma index at server start from `server/kb/`. Glossary lookup uses normalised exact and fuzzy matching on the utterance; tone, empathy, and explainer entries use vector search filtered by language.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| OpenAI embeddings | High quality | Network dependency during demo | Kept as alternative |
| No vector store (keyword only) | Simplest | Misses paraphrased emotions and topics | Weaker tone retrieval |

## Consequences

- **Positive**: offline, fast, predictable.
- **Negative**: model download at setup.
- **Risks and mitigations**: pre-download during setup.

## Implementation

`server/kb/index.py`, `server/kb/retrieve.py`.

## Review Notes

- 2026-10-22, Claude (agent): Drafted as a proposal. Awaiting human review; do not implement until accepted.
