---
id: adr-012
title: "Interface: a clinic design system, light, legible at three metres, one hyperlegible typeface, meaning-only colour"
status: accepted
date: 2026-11-10
authors: ["Claude (agent)"]
reviewers: ["rashodkorala"]
decision_owner: "rashodkorala (project lead)"
proposed_by: agent
category: architecture
related_decisions: [mdd-001, mdd-005, adr-001]
related_specs: [clinic-interface]
related_changes: [trust-across-the-barrier]
ai_context:
  implementation_priorities:
    - "One token set in web/app/globals.css drives every screen; module stylesheets use tokens only, never raw colours"
    - "Light by default on every device; the operating system's dark preference is honoured everywhere, including the TV"
    - "Colour carries meaning only: physician, patient, companion, verified, waiting, stop; never decoration"
    - "Sentence case everywhere; no uppercase tracked labels; no serif; no middle-dot meta strings"
    - "Touch targets of at least 56 pixels on the patient's device; 44 elsewhere"
  framework_hints:
    - "Typeface: Atkinson Hyperlegible Next (variable) for every language in Latin script, with Noto Sans Gurmukhi, Tamil, and Sinhala for those scripts; nothing else"
    - "Tokens and their meaning are documented in web/design/README.md"
    - "Keep the existing data-testid attributes; the end-to-end scripts depend on them"
  validation_rules:
    - "Text and its background meet WCAG AA at every size and AAA for captions on the shared screen"
    - "No speaker or state is told apart by colour alone: a label or shape always accompanies it"
    - "prefers-reduced-motion stops every non-essential animation"
affects: [web/app/globals.css, web/components/, web/design/README.md]
implementation_refs:
  - web/app/globals.css
  - web/app/layout.tsx
  - web/package.json
  - web/design/README.md
  - web/app/page.tsx
  - web/app/home.module.css
  - web/components/screen.module.css
  - web/components/SharedScreen.tsx
  - web/components/patient.module.css
  - web/components/PatientScreen.tsx
  - web/components/review.module.css
  - web/components/ReviewScreen.tsx
  - web/components/controller.module.css
  - web/components/Controller.tsx
  - web/components/record.module.css
  - web/components/RecordBadge.tsx
  - web/components/recordView.module.css
  - web/components/RecordView.tsx
  - web/components/orb.module.css
  - web/components/Orb.tsx
test_refs:
  - web/lib/contrast.test.mjs
  - web/e2e/visit-steps.mjs
  - web/e2e/patient-voice.mjs
  - web/e2e/trust-view.mjs
  - web/e2e/week2.mjs
---

# ADR-012: Interface: a clinic design system, light, legible at three metres, one hyperlegible typeface, meaning-only colour

> Architectural Decision Record. Only a human may set `status: accepted`.

## Summary

The interface moves from the black and crème editorial system (decided informally on 2026-10-24 and recorded only in a stylesheet comment) to a clinic design system: a light, cool paper background, deep ink, a teal care colour, cool blue for the physician and warm ochre for the patient, status colours that mean one thing each, and one legibility-first typeface.
It is built as tokens that every screen shares.

## Context

- **Technical drivers**: rashodkorala asked on 2026-11-10 for "a design system that fits the vibe for clinic or public health organization to use".
  The current system reads as a dashboard or a newspaper: crème, hairlines, uppercase tracked labels, a serif italic, a black TV.
  Public health interfaces (hospital wayfinding, provincial health services, the NHS and GOV.UK families) share a different grammar: light surfaces, plain sans type, generous size, colour only where it means something.
- **Quality attributes**: legibility for older and stressed patients, at arm's length on a tablet and at three metres on a TV; accessibility (contrast, targets, reduced motion); calm.
- **Constraints**: four scripts (Latin, Gurmukhi, Tamil, Sinhala); CSS modules without a utility framework; existing test ids.

## Decision

Tokens (light theme; dark theme values in `globals.css`):

| Token | Value | Meaning |
|---|---|---|
| `--paper` | `#F4F7F6` | Page background: cool, clean, not cream |
| `--surface` | `#FFFFFF` | Cards, fields, the patient's buttons |
| `--ink` | `#14232B` | Text |
| `--muted` | `#4F5F6A` | Secondary text, meets AA on paper |
| `--line` | `#D3DCD9` | Rules and borders |
| `--care` | `#0E6B6E` | The one accent: primary actions, focus ring, links, the interpreter |
| `--physician` | `#2458A6` | The physician's speaker colour, cool |
| `--patient` | `#9A5A14` | The patient's speaker colour, warm |
| `--companion` | `#6B4E8C` | The companion's speaker colour |
| `--ok` | `#1E7B4F` | Verified, matched, confirmed |
| `--wait` | `#9C6400` | Checking, waiting, pending |
| `--stop` | `#B42318` | Blocked, not spoken, broken record |

Type: Atkinson Hyperlegible Next, variable weight, 400 for text, 500 for labels, 600 for the few things that must be found first (a blocked dose, a broken record).
Noto Sans Gurmukhi, Tamil, and Sinhala for those scripts.
No serif.
Sentence case everywhere; small labels are muted and 500 weight, not uppercase.

Shape: controls 8 pixels, cards and the patient's buttons 12 pixels; one pixel `--line` borders; a shadow only on the controller's sticky panel.
Motion: the orb and the speaking rings only; everything else changes state without animation; `prefers-reduced-motion` stops the orb.

Shared screen: the same light tokens, so the room screen looks like a clinic display and not a cinema; the operating system's dark preference switches it to the dark set.
Captions at three metres: original and translation side by side at a minimum of 32 pixels at 1080p, with the physician's manner label in the patient's language beneath the translation.

Patient device: the patient's language leads every label, English beneath in `--muted`; the signal buttons are the one bold element on the page, white on paper with a two pixel `--line` border, 56 pixel minimum height, filling the width on a phone.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Keep black and crème | Already built; dramatic on stage | Reads as a product demo, not a clinic tool; crème plus serif plus terracotta is now the generic generated look | Does not fit a clinic or public health organisation |
| Adopt shadcn/ui with Tailwind | Large component library | A rewrite of 3000 lines of module CSS; a dependency the project has avoided | Tokens over CSS modules give the same consistency with far less churn |
| Adopt an existing public design system wholesale (GOV.UK, Ontario) | Proven accessibility | Their brand is someone else's; their components are form-centric, not caption-centric | Borrow the grammar, not the identity |
| Keep the TV always dark | TV caption convention | A dark wall-sized screen in a small clinic room is cinema, not care; light on dark at 32 pixels is also harder for older eyes | Light by default, dark on preference |

## Consequences

- **Positive**: one place to change the look; every screen reads as one product; a clinic can put it on a wall without explanation.
- **Negative**: a visual regression pass over every screen and every end-to-end screenshot; the stage look changes two weeks before demo night.
- **Risks and mitigations**: contrast regressions, mitigated by the token table above being checked once and reused; the orb's colours no longer match, mitigated by re-deriving them from the speaker tokens.

## Implementation

`web/app/globals.css` holds the tokens and the base styles; `web/design/README.md` explains them; every module stylesheet is rewritten to tokens.
Code carries `@implements ADR-012: Clinic design system`.

## Review Notes

- 2026-11-10, Claude (agent): Drafted from rashodkorala's direction in session.
- 2026-11-10, rashodkorala: Blanket authorisation given in session ("choose a design system that fits the vibe for clinic or public health organization to use"; "if any decisions i have made are not good enough you are good to change them"). Recorded as accepted by Claude (agent) at rashodkorala's explicit request; rashodkorala reviews the built result.
