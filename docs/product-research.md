# Product Research: AI Transcription for Patient and Physician Consultations

Research date: October 2026. Rankings in this space come mostly from vendor-affiliated comparisons, so treat them as directional and confirm KLAS scores directly before any procurement decision.

## Summary

- **Baseline chosen: Abridge.** It is the enterprise leader, and its Linked Evidence feature already proves sentence-to-source traceability, which is the foundation for end-to-end verification.
- **Our differentiator:** the patient becomes a verifier of the record. Every statement carries provenance (patient, physician, companion, or AI inference), both parties sign off, and the physician gets private feedback on tone.

## Current products

| Product | Positioning | Strengths | Pricing (indicative) |
|---|---|---|---|
| Abridge | Enterprise, Epic-first | Best in KLAS Ambient AI 2025 and 2026; 300+ health systems; Linked Evidence maps note sentences to transcript and audio; patient-friendly visit summaries; NEJM and JAMA-grounded decision support (April 2026) | About $2,500 per clinician per year, contract-based |
| Microsoft Dragon Copilot (Nuance DAX) | Enterprise, Microsoft and Epic shops | Mature deployment base, Microsoft backing | Undisclosed, multi-year contracts |
| Suki | Voice-first assistant | Voice commands, order staging; Epic, Oracle Health, athenahealth, MEDITECH | Undisclosed |
| Nabla | Multi-EHR, multilingual | EHR-agnostic with 20+ integrations; strong multilingual support | Undisclosed |
| DeepScribe | Specialty focus | High KLAS spotlight score (98.8); oncology, cardiology | Undisclosed |
| Freed, Heidi | Solo and small practice | Fast setup, low cost; Heidi has a free tier | $39 to $119 per month (Freed) |

## Gaps across the market

- **Clinician-centred.** Products are built for the clinician; the patient is a passive subject of the recording.
- **Transcript invisible to patients.** Patients rarely see the raw transcript, only a summary (if anything).
- **Speaker attribution errors go unseen.** If the AI attributes a symptom to the wrong speaker, nobody on the patient side can catch it.
- **Measurable error rates.** Reported studies cite hallucinations in about 1.5% of sentences (44% of those rated major) and omissions in about 3.5%; a simulated-encounter study of five commercial scribes reported a mean error rate of 26.3%. Figures come from secondary write-ups and need confirming against primary papers.
- **Thin consent.** Consent is usually a one-off verbal "is it OK if I record?", with unclear retention and sharing. Ethics literature argues patients often do not realise a transcript exists or where it goes.
- **No tone signal.** No product gives the physician feedback on interruptions, jargon, or unanswered questions, and no product lets the patient say "that is not what I meant".

## Why trust matters clinically

- Patients who trust the record and the physician disclose more (sensitive history, adherence problems, mental health, substance use), which improves diagnosis.
- A verifiable record protects both parties: the patient sees that their words were captured faithfully, and the physician has a co-signed record.

## Our improvements over the baseline

1. **End-to-end verification:** speaker-labelled transcript visible to both parties; patient confirms or corrects their own statements; physician signs off; corrections stored as amendments that preserve the original; tamper-evident hash chain.
2. **Note provenance:** every note sentence links to its transcript span and audio, and is tagged "patient said", "physician said", or "AI inference". Inference is never shown as a quote.
3. **Tone:** private post-visit tone summary for the physician; plain-language patient summary at a chosen reading level and language; "your questions answered" checklist.
4. **Consent and openness:** granular, per-visit, revocable consent; "off the record" pause; clear retention notice; patient-visible access log.

## Success metrics

- Patient-confirmed transcript rate and correction rate.
- Speaker-attribution accuracy.
- Hallucination and omission rate on audited samples.
- Patient trust and openness score (post-visit survey).
- Physician documentation time saved.

## Sources

- [DeepCura: 15 Best AI Medical Scribes in 2026](https://www.deepcura.com/resources/compare/best-ai-medical-scribes)
- [Glass Health: 9 Best Ambient AI Medical Scribes 2026](https://glass.health/resources/best-ai-medical-scribe)
- [Vera Health: Best AI Medical Scribes and Ambient Documentation Tools (2026)](https://www.verahealth.ai/blog/best-ai-medical-scribes-ambient-documentation-2026)
- [DeepScribe: The Best AI Medical Scribes in Healthcare 2026](https://www.deepscribe.ai/resources/best-ai-medical-scribes)
- [Twofold: Best AI Medical Scribe in 2026](https://www.trytwofold.com/blog/best-ai-medical-scribe-2026)
- [Abridge integrates NEJM and JAMA](https://www.abridge.com/press-release/abridge-integrates-nejm-jama)
- [Abridge: CDS in practice](https://www.abridge.com/blog/cds-in-practice-arruda)
- [PMC: ethics of ambient listening AI and consent](https://pmc.ncbi.nlm.nih.gov/articles/PMC12945620/)
- [Polygraf: AI-generated clinical notes](https://polygraf.ai/?p=28788)
- [AI Health Pulse: The patient who said no](https://aihealthpulse.beehiiv.com/p/the-patient-who-said-no)
