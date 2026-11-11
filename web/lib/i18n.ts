/**
 * @implements ADR-003: Human interpreter escalation on low confidence and high-risk moments
 * @implements CDR-005: Consent and explain-back on the visit channel
 * @implements CDR-006: Record chain entries, review corrections, interpreter dismissal, and presenter controls
 * @implements CDR-007: Clinical note with provenance and patient summary on the visit channel
 * @implements CDR-008: Patient signals, manner, trust updates, companion turns, and the closing check on the visit channel
 * @implements IDR-005: Manner vocabulary and voice delivery
 *
 * Shared screen notices in each visit language. Drafts carry `_reviewer: pending` until a
 * native speaker signs them off, like the knowledge base (task 2.1).
 */

import type { Language, Manner, PatientSignal, Speaker } from "./contracts";
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
  | "micUnavailable"
  // IDR-005: how the physician said it, beneath the translation; plain has no label.
  | "mannerWarm"
  | "mannerReassuring"
  | "mannerGentle"
  | "mannerSerious"
  | "mannerUrgent"
  | "mannerApologetic"
  | "mannerEncouraging"
  // CDR-008: the patient's own controls and the notices each one raises.
  | "signalNotUnderstood"
  | "signalSlower"
  | "signalRepeat"
  | "pause"
  | "resume"
  | "requestInterpreter"
  | "signalNotUnderstoodNotice"
  | "signalSlowerNotice"
  | "signalRepeatNotice"
  | "nothingToRepeat"
  | "signalSent"
  | "yourControls"
  | "latestTitle"
  | "speakerPhysician"
  | "speakerPatient"
  | "speakerCompanion"
  // The quiet line on the patient's device while a turn is still being interpreted.
  | "stageListening"
  | "stageTranslating";

/** IDR-005: the label key for each manner the screens show; plain shows nothing. */
export const MANNER_KEY: Record<Exclude<Manner, "plain">, NoticeKey> = {
  warm: "mannerWarm",
  reassuring: "mannerReassuring",
  gentle: "mannerGentle",
  serious: "mannerSerious",
  urgent: "mannerUrgent",
  apologetic: "mannerApologetic",
  encouraging: "mannerEncouraging",
};

/** The manner label in one language, or null for plain and for a caption without a manner. */
export function mannerLabel(manner: Manner | null | undefined, lang: Language): string | null {
  if (!manner || manner === "plain") return null;
  return notice(MANNER_KEY[manner], lang);
}

/** CDR-008: the control label and the shared-screen notice for each patient signal. */
export const SIGNAL_KEY: Record<PatientSignal, { control: NoticeKey; notice: NoticeKey }> = {
  not_understood: { control: "signalNotUnderstood", notice: "signalNotUnderstoodNotice" },
  slower: { control: "signalSlower", notice: "signalSlowerNotice" },
  repeat: { control: "signalRepeat", notice: "signalRepeatNotice" },
};

/** The speaker as the patient's device names them, in the patient's language. */
export const SPEAKER_KEY: Record<Speaker, NoticeKey> = {
  physician: "speakerPhysician",
  patient: "speakerPatient",
  companion: "speakerCompanion",
};

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
