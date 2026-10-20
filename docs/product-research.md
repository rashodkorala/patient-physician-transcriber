# Product Research: AI Medical Interpretation and Verified Records

Research date: October 2026. Rankings and accuracy claims in this space come mostly from vendors, so treat them as directional and confirm independently before procurement or clinical decisions.

## Summary

- **The core problem is language.** When patient and physician share a language, tone and understanding mostly take care of themselves. When they do not, the patient often relies on a family member (frequently a child), discloses less, and understands less of the plan.
- **Primary market: Canada.** Immigration and linguistic diversity are high, and interpreter access for non-official languages is patchy.
- **The gap:** AI interpreters translate speech but leave no verified record; AI scribes produce a record but do not interpret. No product does both with the patient verifying the record in their own language.
- **Our product:** a live medical interpreter shown on a large in-room screen with bilingual captions, plus a speaker-attributed, bilingual record that both parties verify, with automatic hand-off to a human interpreter when AI translation is not safe enough.

## The language barrier in Canada

- About 69.4% of recent immigrants have a mother tongue other than English or French (2021 census, as reported by an interpretation advocacy brief).
- In Ontario, 265,335 people speak neither English nor French, yet only 3.76% of physicians speak the most common non-official languages (Punjabi, Chinese, Italian, Portuguese, and Spanish).
- In a Windsor, Ontario survey of 530 people, 45% relied on someone to interpret when seeking care, mostly family members and often children, causing misunderstanding and strain.
- French speakers in mainly English-speaking regions also face barriers, and some delay care rather than use an interpreter.
- Health Canada notes the best communication happens when provider and patient share a language, and that interpretation will always be needed for some patients. Rights to interpreters for minority-language speakers are less clear than for Deaf patients.

## Current products

### AI scribes (record, no interpretation)

| Product | Positioning | Strengths |
|---|---|---|
| Abridge | Enterprise leader, Epic-first | Best in KLAS Ambient AI 2025 and 2026; 300+ health systems; Linked Evidence maps note sentences to transcript and audio; patient summaries; multilingual transcription |
| Microsoft Dragon Copilot (Nuance DAX) | Enterprise, Microsoft and Epic | Mature deployment base |
| Suki | Voice-first assistant | Voice commands, order staging |
| Nabla | Multi-EHR, multilingual | EHR-agnostic, 20+ integrations, multilingual notes |
| DeepScribe | Specialty focus | High KLAS spotlight score |
| Freed, Heidi | Solo and small practice | Low cost ($39 to $119 per month for Freed; Heidi free tier) |

### AI interpreters (interpretation, no verified record)

| Product | Positioning | Strengths | Limits |
|---|---|---|---|
| No Barrier | Speech-to-speech AI medical interpreter | 295+ languages and dialects; runs on existing tablets | Vendor itself notes policy may require human interpreters for high-risk encounters and consent |
| Care to Translate | Clinical translation app | Live Translate across 130+ languages; verified medical phrase library | Phrase library is fixed; live mode is AI-only |
| Sully (Medical Interpreter) | AI medical assistant suite | Real-time translation in 20+ languages | Narrow language coverage |
| Google Translate, Microsoft Translator, DeepL | General purpose | Broad coverage, free or cheap | Not built for clinical safety or PHI |
| Human services (phone, video, in person) | Gold standard | Professional accuracy, cultural mediation | Cost, wait times, limited availability for less common languages |

**Baselines chosen:** Abridge for the verified record (Linked Evidence proves sentence-to-source traceability) and No Barrier for interpretation (widest language coverage and an explicit human-escalation stance).

## Machine translation safety evidence

- UCSF (BMJ Quality and Safety): GPT-4 and Google Translate on discharge instructions in Spanish, Chinese, and Russian showed potential for harm of 1% or less per sentence and 6% or less per instruction set; GPT was more accurate in Chinese and Russian.
- Pediatrics (2024): low clinically significant error rates for Spanish and Portuguese, similar to professional translation, but higher risk for Haitian Creole and other languages with a small digital footprint.
- Inpatient study (2025): GPT-4o weakest for Armenian and Somali; human-in-the-loop translation matched or beat professional translation in all six languages.
- Clinical guidance (UW and Harborview): do not use Google Translate or LLMs without oversight and verification from a certified translator.

**Implication:** translation quality must be managed per language. High-resource languages (Spanish, Portuguese, Mandarin) can run with AI plus verification; lower-resource languages (likely Sinhala, and possibly Tamil, Punjabi, Urdu, and Tagalog for medical vocabulary) need stricter thresholds and easier human escalation. Tiers must be set by our own benchmark, not assumed.

## Gaps across the market

- No product combines live interpretation with a verified, speaker-attributed record.
- The patient cannot check, in their own language, what was recorded about them.
- No product confirms comprehension (for example by having the patient explain the plan back in their own words).
- Numbers, doses, and dates are the highest-risk content in translation, yet are rarely read back.
- Speaker attribution and AI hallucination errors stay invisible to the patient. Reported studies cite hallucinations in about 1.5% of note sentences (44% rated major) and omissions in about 3.5%.
- Consent is usually a single verbal question in the physician's language.
- Nothing tells the physician when their meaning, warmth, or certainty was lost in translation.

## Our improvements over the baselines

1. **Live medical interpretation on a shared screen:** bilingual captions side by side on a TV or monitor, translated speech spoken aloud, medical glossary, read-back of numbers and doses, a step where the patient explains the plan back in their own words, and hand-off to a human interpreter.
2. **Bilingual verified record:** each segment keeps the original speech and its translation; the patient verifies in their own language; corrections preserve originals.
3. **Note provenance across languages:** every note sentence links to the original-language speech and its translation, tagged as patient-stated, physician-stated, or AI inference.
4. **Communication across languages:** private feedback to the physician on jargon, idioms that translate badly, lost empathy or certainty, and signs of misunderstanding.
5. **Consent and summaries in the patient's language,** with a patient-visible access log and tamper-evident audit trail.

## Success metrics

- Share of visits completed without a family member interpreting.
- Comprehension check pass rate on the first attempt.
- Translation error rate on audited segments, per language.
- Human interpreter escalation rate and time to connect.
- Patient-confirmed transcript rate and correction rate.
- Patient trust and openness score (post-visit survey in the patient's language).
- Physician documentation time saved.

## Sources

- [Health Canada: Language Barriers in Access to Health Care](https://www.canada.ca/en/health-canada/services/health-care-system/reports-publications/health-care-accessibility/language-barriers.html)
- [Interpretation advocacy brief (census figure)](https://n4.ic12.esolg.ca/en/our-tools/resources/documents/Interpretation-TwoPager.FINAL.pdf)
- [Access to interpretation increases healthcare efficiency and equity](https://n4.ic12.esolg.ca/en/our-tools/summary-document-access-to-interpretation-increases-healthcare-efficiency-and-equity.aspx)
- [McMaster Global Health review (Ontario physician language data)](https://journals.mcmaster.ca/ghar/article/download/1715/1391/4047)
- [Immigration.ca: language barriers in immigrant health care](https://immigration.ca/addressing-the-language-barriers-in-immigrant-health-care/)
- [French-speaking immigrants accessing care (PMC)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3509478/)
- [CHSSN: the francophone experience](https://chssn.org/documents/impact-of-language-barriers-on-access-to-healthcare-services-the-francophone-experience-in-canada/)
- [No Barrier: medical interpretation](https://www.nobarrier.ai/medical-interpretation)
- [No Barrier: AI in medical translation](https://www.nobarrier.ai/post/ai-in-medical-translation-capabilities-and-limitations)
- [Care to Translate](https://www.caretotranslate.com/)
- [Sully: medical interpreter](https://www.sully.ai/ai-medical-employees/sully-the-medical-interpreter)
- [Best AI medical translators 2026: clinical safety comparison](https://www.machinetranslation.com/blog/best-ai-medical-translators)
- [UTHealth AI Translator](https://www.uth.edu/center-for-digital-healthcare-innovation/solutions/ai-translator)
- [AMN Healthcare: language services through AI](https://www.amnhealthcare.com/blog/language-interpreters/transforming-healthcare-language-services-through-ai/)
- [BMJ Quality and Safety: machine translation of discharge instructions](https://qualitysafety.bmj.com/content/35/3/150)
- [AAP: machine translation for pediatric discharge instructions](https://www.aap.org/en/news-room/news-releases/pediatrics2/2024/research-evaluates-use-of-machine-language-translation-platforms-for-pediatric-discharge-instructions)
- [West J Emerg Med: Albanian, Portuguese, and Vietnamese study](https://journalpub.escholarship.org/westjem/article/48825/galley/50357/download/)
- [PMC: inpatient translation across six languages](https://pmc.ncbi.nlm.nih.gov/articles/PMC12552660/)
- [EthnoMed: guidance on machine translation](https://ethnomed.org/?p=8889)
- [DeepCura: Best AI Medical Scribes 2026](https://www.deepcura.com/resources/compare/best-ai-medical-scribes)
- [Glass Health: Best Ambient AI Medical Scribes 2026](https://glass.health/resources/best-ai-medical-scribe)
- [DeepScribe: Best AI Medical Scribes 2026](https://www.deepscribe.ai/resources/best-ai-medical-scribes)
- [Abridge integrates NEJM and JAMA](https://www.abridge.com/press-release/abridge-integrates-nejm-jama)
- [PMC: ethics of ambient listening AI and consent](https://pmc.ncbi.nlm.nih.gov/articles/PMC12945620/)
- [Polygraf: AI-generated clinical notes](https://polygraf.ai/?p=28788)
