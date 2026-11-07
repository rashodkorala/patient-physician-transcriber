import type { Language, PatientLanguage } from "./contracts";

export const LANGUAGE_LABELS: Record<Language, { own: string; english: string }> = {
  "pa-IN": { own: "ਪੰਜਾਬੀ", english: "Punjabi" },
  "fr-CA": { own: "Français", english: "French" },
  "en-CA": { own: "English", english: "English" },
  "si-LK": { own: "සිංහල", english: "Sinhala" },
  "ta-LK": { own: "தமிழ்", english: "Tamil" },
};

/**
 * The thirteen roadmap languages in their own scripts, for the language picker. Punjabi, French,
 * and Tamil are live; Sinhala only when the server started in test mode; the rest are coming soon.
 * @implements TDM-003: Sinhala and Tamil as test-only languages before demo night
 * @implements TDM-004: Tamil is the chosen live language, alongside Punjabi and French, spoken by ElevenLabs
 */
export const ROADMAP: { own: string; english: string; language?: PatientLanguage; test?: boolean }[] = [
  { own: "English", english: "English" },
  { own: "Français", english: "French", language: "fr-CA" },
  { own: "普通话", english: "Mandarin" },
  { own: "粵語", english: "Cantonese" },
  { own: "ਪੰਜਾਬੀ", english: "Punjabi", language: "pa-IN" },
  { own: "اردو", english: "Urdu" },
  { own: "العربية", english: "Arabic" },
  { own: "فارسی", english: "Farsi" },
  { own: "Tagalog", english: "Tagalog" },
  { own: "Español", english: "Spanish" },
  { own: "Português", english: "Portuguese" },
  { own: "සිංහල", english: "Sinhala", language: "si-LK", test: true },
  { own: "தமிழ்", english: "Tamil", language: "ta-LK" },
];

/**
 * Neural voices per language. Confirm each one on the demo laptop (task 1.3).
 * @implements ADR-005: Speech: Azure Speech primary, Google Speech backup
 */
export const VOICES: Record<Language, string> = {
  "pa-IN": "pa-IN-VaaniNeural",
  "fr-CA": "fr-CA-SylvieNeural",
  "en-CA": "en-CA-ClaraNeural",
  // Sinhala is a TDM-003 test language; Tamil (TDM-004) is Sri Lankan Tamil, as the test patient speaks it.
  "si-LK": "si-LK-ThiliniNeural",
  "ta-LK": "ta-LK-SaranyaNeural",
};
