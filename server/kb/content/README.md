# Knowledge base content (ADR-002)

Curated content the translation pipeline retrieves on every turn.
Every Punjabi and French entry is a draft by Claude until a native speaker reviews it.
A reviewer replaces `reviewer: pending` with their name and the date.
Task 2.1 is complete only when every file names a reviewer.

- `glossary/en-<lang>.yaml`: medical terms with the approved translation and a plain-language explanation in each language.
- `tone/<lang>.md`: register, forms of address, delivering news, sensitive topics, and idioms to avoid; one `##` section per retrievable chunk.
- `empathy/<lang>.yaml`: checked phrases for reassurance, acknowledgement, apology, and encouragement.
- `conditions/<condition>.md`: plain-language condition explainers, one `## <language code>` section per language.
