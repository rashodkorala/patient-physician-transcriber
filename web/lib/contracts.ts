/**
 * Wire contracts mirrored from server/contracts.py.
 *
 * @implements CDR-001: Visit WebSocket event contract
 * @implements CDR-002: Turn result schema
 * @contract ws:/ws/visit
 * @contract TurnResult
 * @contract TurnCaption
 * @see openspec/tdr/cdr/cdr-001-visit-websocket-events.md
 * @see openspec/tdr/cdr/cdr-002-turn-result-schema.md
 */

export type Language = "pa-IN" | "fr-CA" | "en-CA";
export type PatientLanguage = "pa-IN" | "fr-CA";
export type Speaker = "patient" | "physician" | "companion";
export type ToneTag = "reassuring" | "respectful" | "empathetic" | "neutral" | "urgent" | "uncertain";
export type ToneLabel = "respectful" | "reassuring" | "empathetic" | "neutral";
export type Emotion = "calm" | "worried" | "embarrassed" | "in_pain" | "relieved" | "confused";
export type Certainty = "high" | "medium" | "low";
export type CriticalKind = "dose" | "unit" | "frequency" | "date" | "number" | "medication";
export type TurnStatusValue = "final" | "readback_required" | "blocked" | "escalated";
export type CaptionStatus = "final" | "blocked" | "escalated";
export type Role = "controller" | "screen" | "review";

export interface GlossaryEntry {
  term: string;
  translation: string;
  explanation: string;
}

export interface CriticalValue {
  kind: CriticalKind;
  source: string;
  translated: string;
  matched: boolean;
}

/** Full turn: server and physician controller only (turn.analysis). */
export interface TurnResult {
  turnId: string;
  speaker: Speaker;
  sourceLanguage: Language;
  targetLanguage: Language;
  sourceText: string;
  translation: string;
  backTranslation: string;
  toneTags: ToneTag[];
  emotion: Emotion;
  certainty: Certainty;
  glossaryUsed: GlossaryEntry[];
  criticalValues: CriticalValue[];
  confidence: number;
  status: TurnStatusValue;
  attempts: number;
}

/** Public projection: every screen (turn.result). */
export interface TurnCaption {
  turnId: string;
  speaker: Speaker;
  sourceLanguage: Language;
  targetLanguage: Language;
  sourceText: string;
  status: CaptionStatus;
  translation: string | null;
  toneLabel: ToneLabel | null;
  glossaryUsed: GlossaryEntry[];
  criticalValues: { kind: string; source: string; translated: string }[];
  readbackConfirmed: boolean;
}

export interface RecordIntegrity {
  status: "verified" | "broken";
  headHash: string;
  brokenAt?: string | null;
}

export interface EmpathyNudge {
  turnId: string;
  emotion: Emotion;
  suggestion: string;
  phrase: string;
  phraseLanguage: Language;
}

export interface VisitStateController {
  patientLanguage: PatientLanguage;
  physicianLanguage: Language;
  consent: string | null;
  paused: boolean;
  turns: TurnResult[];
  currentTurn?: TurnResult | null;
  pendingReadback?: string | null;
  nudges: EmpathyNudge[];
  integrity: RecordIntegrity;
}

export interface VisitStatePublic {
  patientLanguage: PatientLanguage;
  physicianLanguage: Language;
  consent: string | null;
  paused: boolean;
  turns: TurnCaption[];
  currentTurn?: { turnId: string; speaker: Speaker; sourceText: string; stage: string } | null;
  integrity: RecordIntegrity;
}

export interface TurnStarted {
  turnId: string;
  speaker: Speaker;
  language: Language;
}

export interface TurnStatus {
  turnId: string;
  stage: string;
}

export interface ErrorPayload {
  message: string;
  command?: string | null;
}

export interface Envelope<P = unknown> {
  type: string;
  visitId: string;
  seq: number;
  ts: string;
  payload: P;
}

export interface SetLanguages {
  patientLanguage: PatientLanguage;
  physicianLanguage: "en-CA";
}

export interface TurnSubmit {
  speaker: Speaker;
  language: Language;
  text: string;
  recognitionConfidence: number;
}
