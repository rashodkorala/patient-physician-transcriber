/**
 * Wire contracts mirrored from server/contracts.py.
 *
 * @implements CDR-001: Visit WebSocket event contract
 * @implements CDR-002: Turn result schema
 * @implements CDR-003: Participant names and interpreter lines on the visit channel
 * @implements CDR-004: Interpreter voice playback on the visit channel
 * @implements TDM-002: Presenter mismatch control for the blocked-dose beat
 * @contract ws:/ws/visit
 * @contract TurnResult
 * @contract TurnCaption
 * @see openspec/tdr/cdr/cdr-001-visit-websocket-events.md
 * @see openspec/tdr/cdr/cdr-002-turn-result-schema.md
 * @see openspec/tdr/cdr/cdr-003-names-and-interpreter-lines.md
 * @see openspec/tdr/cdr/cdr-004-interpreter-voice-playback-events.md
 */

export type Language = "pa-IN" | "fr-CA" | "en-CA" | "si-LK" | "ta-LK";
export type PatientLanguage = "pa-IN" | "fr-CA" | "si-LK" | "ta-LK";
export type Speaker = "patient" | "physician" | "companion";
export type ToneTag = "reassuring" | "respectful" | "empathetic" | "neutral" | "urgent" | "uncertain";
export type ToneLabel = "respectful" | "reassuring" | "empathetic" | "neutral";
export type Emotion = "calm" | "worried" | "embarrassed" | "in_pain" | "relieved" | "confused";
export type Certainty = "high" | "medium" | "low";
export type CriticalKind = "dose" | "unit" | "frequency" | "date" | "number" | "medication";
export type TurnStatusValue = "final" | "readback_required" | "blocked" | "escalated";
export type CaptionStatus = "final" | "blocked" | "escalated";
export type Role = "controller" | "screen" | "review";
export type IntroductionState = "pending" | "asking_physician" | "asking_patient" | "done" | "skipped";
export type NameRole = "physician" | "patient";
export type LinePurpose = "introduction" | "ask_physician_name" | "ask_patient_name" | "welcome";

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
  // CDR-003: optional, so a server built before names still satisfies this type.
  physicianName?: string | null;
  patientName?: string | null;
  introduction?: IntroductionState;
  // CDR-004: optional, so a server built before voice playback still satisfies this type.
  speaking?: VoiceSpeaking | null;
}

export interface VisitStatePublic {
  patientLanguage: PatientLanguage;
  physicianLanguage: Language;
  consent: string | null;
  paused: boolean;
  turns: TurnCaption[];
  currentTurn?: { turnId: string; speaker: Speaker; sourceText: string; stage: string } | null;
  integrity: RecordIntegrity;
  // CDR-003: optional, so a server built before names still satisfies this type.
  physicianName?: string | null;
  patientName?: string | null;
  introduction?: IntroductionState;
  // CDR-004: optional, so a server built before voice playback still satisfies this type.
  speaking?: VoiceSpeaking | null;
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

export type EscalationReason = "low_confidence" | "tone_failure" | "high_risk" | "requested";

export interface InterpreterEscalation {
  reason: EscalationReason;
  turnId?: string | null;
}

/** visit.mark_high_risk, controller only: the server records it and offers an interpreter (reason high_risk). */
export interface MarkHighRisk {
  turnId?: string | null;
  note?: string | null;
}

/** demo.injection_state, controller only (TDM-002): the presenter's one-shot mismatch injection. */
export interface DemoInjectionState {
  state: "armed" | "fired" | "cancelled";
}

/** turn.readback_required, turn.readback_confirm, and turn.readback_reject. */
export interface TurnRef {
  turnId: string;
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

/** visit.names; as visit.set_names a field left out keeps its name and "" or null clears it. */
export interface Names {
  physicianName?: string | null;
  patientName?: string | null;
}

export const NAME_MAX = 60;

/** interpreter.line: something the interpreter says itself, in each language it is spoken in. */
export interface InterpreterLine {
  lineId: string;
  purpose: LinePurpose;
  lines: { language: Language; text: string }[];
}

/** visit.name_proposed, controller only: a name heard in a reply, waiting for confirmation. */
export interface NameProposed {
  role: NameRole;
  name: string;
}

export interface NameReply {
  role: NameRole;
  text: string;
}

/** visit.name_confirm and visit.name_reject. */
export interface NameRef {
  role: NameRole;
}

export interface TurnSubmit {
  speaker: Speaker;
  language: Language;
  text: string;
  recognitionConfidence: number;
}

/** voice.started and voice.ended, controller only: what the interpreter's voice began or stopped playing. */
export interface VoicePlayback {
  speechId: string;
  language: Language;
}

/** voice.speaking, and visit.state.speaking: whether the interpreter's voice is playing; every role. */
export type VoiceSpeaking =
  | { speaking: true; speechId: string; language: Language }
  | { speaking: false; speechId: null; language: null };
