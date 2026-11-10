/**
 * @implements ADR-003: Human interpreter escalation on low confidence and high-risk moments
 * @implements CDR-005: Consent and explain-back on the visit channel
 * @implements CDR-006: Record chain entries, review corrections, interpreter dismissal, and presenter controls
 * @implements CDR-007: Clinical note with provenance and patient summary on the visit channel
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
  | "interpreterSimulated"
  // CDR-005: the content-free explain-back prompt on the shared and review screens.
  | "explainBackListening"
  | "explainBackChecking"
  // CDR-006 and CDR-007: the patient's review screen and the summary.
  | "reviewTitle"
  | "transcriptTitle"
  | "consentAgree"
  | "confirm"
  | "confirmed"
  | "correct"
  | "correctStop"
  | "correctionChecking"
  | "correctionRefused"
  | "corrected"
  | "history"
  | "original"
  | "correction"
  | "repeatedBelow"
  | "summaryTitle"
  | "summaryPreparing"
  | "summaryRefused"
  | "summaryStale"
  | "listen"
  | "stop"
  | "refusedBusy"
  | "refusedNotCurrent"
  | "refusedGeneric"
  | "micUnavailable";

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

/** The notice in one language. */
export function notice(key: NoticeKey, lang: Language): string {
  return NOTICES[lang][key];
}
