/**
 * Shared screen notices in each visit language. Drafts carry `_reviewer: pending` until a
 * native speaker signs them off, like the knowledge base (task 2.1).
 */

import type { Language } from "./contracts";
import en from "@/i18n/en.json";
import fr from "@/i18n/fr.json";
import pa from "@/i18n/pa.json";

export type NoticeKey = "checkingDose" | "pleaseRepeat" | "interpreterOffered";

const NOTICES: Record<Language, Record<NoticeKey, string>> = { "en-CA": en, "fr-CA": fr, "pa-IN": pa };

/** The notice in each of the turn's two languages, the speaker's first. */
export function bilingual(key: NoticeKey, first: Language, second: Language): { lang: Language; text: string }[] {
  return [first, second].map((lang) => ({ lang, text: NOTICES[lang][key] }));
}
