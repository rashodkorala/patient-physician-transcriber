import type { Language } from "./contracts";

export const LANGUAGE_LABELS: Record<Language, { own: string; english: string }> = {
  "pa-IN": { own: "ਪੰਜਾਬੀ", english: "Punjabi" },
  "fr-CA": { own: "Français", english: "French" },
  "en-CA": { own: "English", english: "English" },
};

/**
 * Neural voices per language. Confirm each one on the demo laptop (task 1.3).
 * @implements ADR-005: Speech: Azure Speech primary, Google Speech backup
 */
export const VOICES: Record<Language, string> = {
  "pa-IN": "pa-IN-VaaniNeural",
  "fr-CA": "fr-CA-SylvieNeural",
  "en-CA": "en-CA-ClaraNeural",
};
