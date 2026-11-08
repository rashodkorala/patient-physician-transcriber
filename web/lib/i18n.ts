/**
 * @implements ADR-003: Human interpreter escalation on low confidence and high-risk moments
 *
 * Shared screen notices in each visit language. Drafts carry `_reviewer: pending` until a
 * native speaker signs them off, like the knowledge base (task 2.1).
 */

import type { Language } from "./contracts";
import en from "@/i18n/en.json";
import fr from "@/i18n/fr.json";
import pa from "@/i18n/pa.json";
import si from "@/i18n/si.json";
import ta from "@/i18n/ta.json";

export type NoticeKey =
  | "checkingDose"
  | "pleaseRepeat"
  | "interpreterOffered"
  | "ready"
  | "paused"
  | "interpreterAvailable"
  | "interpreterConnecting"
  | "interpreterSimulated";

/**
 * ADR-003: the demo's interpreter call is simulated. Every screen starts these timers when it receives
 * `interpreter.escalation` with reason `requested`, so the TV and the controller show each notice together:
 * connecting for CONNECTING_MS, then "would join here (simulated)" for SIMULATED_MS, then the visit goes on.
 */
export const INTERPRETER_CONNECTING_MS = 4000;
export const INTERPRETER_SIMULATED_MS = 6000;
export type InterpreterPhase = "offered" | "connecting" | "simulated";

const NOTICES: Record<Language, Record<NoticeKey, string>> = {
  "en-CA": en,
  "fr-CA": fr,
  "pa-IN": pa,
  "si-LK": si,
  "ta-LK": ta,
};

/** The notice in each of the turn's two languages, the speaker's first. */
export function bilingual(key: NoticeKey, first: Language, second: Language): { lang: Language; text: string }[] {
  return [first, second].map((lang) => ({ lang, text: NOTICES[lang][key] }));
}
