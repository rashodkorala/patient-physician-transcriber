---
id: adr-002
title: "Knowledge base feeding translation: glossary, tone and culture, empathy, condition explainers"
status: accepted
date: 2026-10-22
authors: ["rashodkorala"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: human
category: architecture
related_decisions: [adr-001]
related_specs: [demo-consultation-flow]
related_changes: [demo-night-mvp]
ai_context:
  implementation_priorities:
    - "Translation must use approved glossary terms and respectful register"
    - "Warmth, reassurance, and certainty must survive translation"
  framework_hints:
    - "Content in server/kb/ as Markdown and YAML, reviewed by native speakers"
    - "Storage and retrieval method: see IDR-002"
  validation_rules:
    - "Critical values are never altered by knowledge base content"
    - "Every knowledge base entry has a reviewer"
affects: [server/kb/]
implementation_refs: []
test_refs: []
---

# ADR-002: Knowledge base feeding translation: glossary, tone and culture, empathy, condition explainers

## Summary

A curated knowledge base gives the translation pipeline medical terms, tone and culture guidance, empathy phrases, and plain-language condition explainers for Punjabi, French, and English.

## Context

- **Technical drivers**: plain machine translation loses empathy, respect, and affirmation, which matter for patient trust.
- **Quality attributes**: accuracy of medical terms; culturally respectful tone.
- **Constraints**: small team; content must be checked by the Punjabi and French speakers.

## Decision

Maintain four knowledge sets per language: medical glossary (term, approved translation, plain explanation), tone and culture guides (honorifics such as Punjabi 'ji' and 'tusi' or 'aap', French 'vous'; delivering bad news; sensitive topics; idioms to avoid), an empathy phrase bank (reassurance, acknowledgement, apology, encouragement), and condition explainers for the demo conditions. The translation pipeline retrieves relevant entries for every turn.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Prompt-only (no knowledge base) | Fastest to build | Inconsistent terms and tone; nothing to review | No control over quality |
| Fine-tuned translation model | Potentially best quality | Weeks of work and data we do not have | Too slow for demo |

## Consequences

- **Positive**: reviewable, improvable translation quality; a visible differentiator.
- **Negative**: content work for native speakers.
- **Risks and mitigations**: start with the demo script's terms only.

## Implementation

`server/kb/` content plus the retrieve node in the turn graph (ADR-004, IDR-002).

## Review Notes

- 2026-10-22, rashodkorala: Accepted by the project lead in the planning conversation.
