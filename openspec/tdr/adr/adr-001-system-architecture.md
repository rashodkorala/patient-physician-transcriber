---
id: adr-001
title: "Architecture: Python FastAPI server, Next.js front end, shared TV screen client"
status: accepted
date: 2026-10-22
authors: ["rashodkorala"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: human
category: architecture
related_decisions: [mdd-001, mdd-003]
related_specs: [demo-consultation-flow]
related_changes: [demo-night-mvp]
ai_context:
  implementation_priorities:
    - "Server owns visit state and all AI calls"
    - "Front end is screens only"
  framework_hints:
    - "server/: Python, FastAPI, LangChain"
    - "web/: Next.js, TypeScript"
    - "Screens: /control, /screen, /review, /record"
  validation_rules:
    - "No API keys in the browser except short-lived speech tokens"
    - "Front end never calls LLMs directly"
affects: [server/, web/]
implementation_refs: []
test_refs: []
---

# ADR-001: Architecture: Python FastAPI server, Next.js front end, shared TV screen client

## Summary

A Python FastAPI server runs the AI pipeline, knowledge base, and visit state; a Next.js front end provides the physician controller, the TV screen, and the patient review screens.

## Context

- **Technical drivers**: the user wants a server with LangChain and a knowledge base; Python has the strongest LangChain, LangGraph, and embeddings ecosystem.
- **Quality attributes**: low latency per turn, demo reliability.
- **Constraints**: runs locally on one laptop; TV and phone connect over the local network.

## Decision

Two processes on the demo laptop: `server/` (FastAPI, LangChain, knowledge base, visit state, speech token minting) and `web/` (Next.js). The TV shows `/screen` in a full-screen browser; the laptop runs `/control`; a phone may open `/review`.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Single Next.js app with API routes | One process | Weaker Python AI ecosystem; user asked for a server | Rejected by user direction |
| Python server with plain HTML front end | Simplest | Harder to build polished TV and phone screens | Next.js gives better UI speed |

## Consequences

- **Positive**: clean split; AI work stays in Python.
- **Negative**: two runtimes to install and start.
- **Risks and mitigations**: one start script; contracts between them in CDR-001 and CDR-002.

## Implementation

Server and screens communicate only through the contracts in CDR-001 and CDR-002.

## Review Notes

- 2026-10-22, rashodkorala: Accepted by the project lead in the planning conversation.
