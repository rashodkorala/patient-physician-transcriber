/**
 * Wire contracts mirrored from server/contracts.py.
 *
 * @implements CDR-001: Visit WebSocket event contract
 * @implements CDR-002: Turn result schema
 * @implements CDR-003: Participant names and interpreter lines on the visit channel
 * @implements CDR-004: Interpreter voice playback on the visit channel
 * @implements TDM-002: Presenter mismatch control for the blocked-dose beat
 * @implements CDR-005: Consent and explain-back on the visit channel
 * @implements CDR-006: Record chain entries, review corrections, interpreter dismissal, and presenter controls
 * @implements CDR-007: Clinical note with provenance and patient summary on the visit channel
 * @implements TDM-005: Hidden record-tamper control for the demo
 * @implements CDR-008: Patient signals, manner, trust updates, companion turns, and the closing check on the visit channel
 * @implements IDR-005: Manner vocabulary and voice delivery
 * @contract ws:/ws/visit
 * @contract TurnResult
 * @contract TurnCaption
 * @see openspec/tdr/cdr/cdr-008-patient-voice-manner-and-trust-events.md
 * @see openspec/tdr/cdr/cdr-001-visit-websocket-events.md
 * @see openspec/tdr/cdr/cdr-002-turn-result-schema.md
 * @see openspec/tdr/cdr/cdr-003-names-and-interpreter-lines.md
 * @see openspec/tdr/cdr/cdr-004-interpreter-voice-playback-events.md
 * @see openspec/tdr/cdr/cdr-005-consent-and-explain-back-events.md
 * @see openspec/tdr/cdr/cdr-006-record-entries-review-corrections-and-tamper.md
 * @see openspec/tdr/cdr/cdr-007-clinical-note-and-patient-summary.md
 * @see openspec/tdr/tdm/tdm-005-hidden-record-tamper-control.md
 */

export type Language = "pa-IN" | "fr-CA" | "en-CA" | "si-LK" | "ta-LK";
export type PatientLanguage = "pa-IN" | "fr-CA" | "si-LK" | "ta-LK";
export type Speaker = "patient" | "physician" | "companion";
export type ToneTag = "reassuring" | "respectful" | "empathetic" | "neutral" | "urgent" | "uncertain";
export type ToneLabel = "respectful" | "reassuring" | "empathetic" | "neutral";
export type Emotion = "calm" | "worried" | "frightened" | "embarrassed" | "in_pain" | "relieved" | "confused";
/** IDR-005: how a turn was said, read from the words; plain is the default. */
export type Manner = "plain" | "warm" | "reassuring" | "gentle" | "serious" | "urgent" | "apologetic" | "encouraging";
export const MANNERS: Manner[] = ["plain", "warm", "reassuring", "gentle", "serious", "urgent", "apologetic", "encouraging"];
/** CDR-008: the patient's own signals during the visit. */
export type PatientSignal = "not_understood" | "slower" | "repeat";
export const PATIENT_SIGNALS: PatientSignal[] = ["not_understood", "slower", "repeat"];
export type TrustCueKind = "reassurance" | "understanding" | "culture";
export type Certainty = "high" | "medium" | "low";
export type CriticalKind = "dose" | "unit" | "frequency" | "date" | "number" | "medication";
// ADR-003 (amended 2026-11-12): unclear is a confidence failure that survived the retry, before the third in a row.
export type TurnStatusValue = "final" | "readback_required" | "blocked" | "escalated" | "unclear";
export type CaptionStatus = "final" | "blocked" | "escalated" | "unclear";
export type Role = "controller" | "screen" | "review";
export type IntroductionState = "pending" | "asking_physician" | "asking_patient" | "done" | "skipped";
export type NameRole = "physician" | "patient";
export type LinePurpose =
  | "introduction"
  | "ask_physician_name"
  | "ask_patient_name"
  | "welcome"
  // CDR-008: the interpreter relays a patient signal to the physician, and asks the patient if anything is unclear.
  | "signal_not_understood"
  | "signal_slower"
  | "ask_if_clear"
  // ADR-003 and CDR-003: the interpreter asks the speaker of an unclear turn to say it again, in their language.
  | "ask_to_repeat";

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
  /** IDR-005: how the speaker said it, read from the words. Optional so an older server still satisfies the type. */
  manner?: Manner;
  /** ADR-003 and CDR-002: the speaker's unclear streak after this turn; controller only, never in TurnCaption. */
  unclearStreak?: number;
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
  /** CDR-008: the physician's manner on a final physician turn only; null for every patient or companion turn. */
  manner?: Manner | null;
}

// ---------- CDR-008: patient signals and trust updates ----------

/** patient.signal command, from the patient's device (review role) only. */
export interface PatientSignalCommand {
  signal: PatientSignal;
}

/** patient.signal event to every role, and the body of a `signal` chain entry. */
export interface PatientSignalEntry {
  signalId: string;
  signal: PatientSignal;
  afterTurnId: string | null;
  at: string;
}

export const TRUST_CUE_MAX = 200;

/** A short English suggestion for the physician only. */
export interface TrustCue {
  kind: TrustCueKind;
  text: string;
}

/** trust.update, controller only: one per settled final turn, and one per accepted patient signal. */
export interface TrustUpdate {
  turnId: string | null;
  speaker: Speaker | null;
  emotion: Emotion | null;
  manner: Manner | null;
  reassuranceLanded: boolean | null;
  signal: PatientSignal | null;
  cue: TrustCue | null;
  at: string;
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
  // CDR-005 and CDR-006: optional, so a server built before consent and the record chain still satisfies this type.
  consentNotice?: ConsentNotice | null;
  consentState?: ConsentState | null;
  interpreterOpen?: boolean;
  injection?: InjectionStatus | null;
  escalations?: EscalationEntry[];
  segments?: SegmentHistoryController[];
  tamper?: TamperState | null;
  // CDR-005 explain-back and CDR-007: optional, so an older server still satisfies this type.
  explainBack?: ExplainBackState | null;
  explainBackResults?: ExplainBackResult[];
  note?: ClinicalNote | null;
  noteStale?: boolean;
  summaryChecks?: SummaryCheck[];
  summary?: PatientSummary | null;
  summaryStale?: boolean;
  // CDR-008: the patient's signals for every role, and the trust timeline for the controller only.
  signals?: PatientSignalEntry[];
  trust?: TrustUpdate[];
  // ADR-003 and CDR-002: each speaker's unclear streak, controller only.
  unclearStreak?: Partial<Record<Speaker, number>>;
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
  // CDR-005 and CDR-006: optional, so a server built before consent and the record chain still satisfies this type.
  consentNotice?: ConsentNotice | null;
  consentState?: ConsentState | null;
  interpreterOpen?: boolean;
  // CDR-006, CDR-005 explain-back, and CDR-007: optional, so an older server still satisfies this type.
  segments?: SegmentHistory[];
  explainBack?: ExplainBackState | null;
  summary?: PatientSummary | null;
  summaryStale?: boolean;
  // CDR-008: the patient's signals; never the trust timeline.
  signals?: PatientSignalEntry[];
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

// ---------- CDR-005: consent ----------

export type ConsentBy = "patient" | "physician_on_behalf";

/** The reviewed notice for the visit's patient language: lines hold the patient language first, English second. */
export interface ConsentNotice {
  noticeId: string;
  speechId: string;
  version: string;
  language: PatientLanguage;
  lines: { language: Language; text: string }[];
}

/** consent.speak, controller only: play the notice now, by its speech id. */
export interface ConsentSpeak {
  speechId: string;
  language: PatientLanguage;
}

/** consent.give, from the review screen (the patient) or the controller (on the patient's behalf). */
export interface ConsentGive {
  noticeVersion: string;
  language: PatientLanguage;
}

/** consent.withdraw; the reason is at most 200 characters and kept in the record only. */
export interface ConsentWithdraw {
  reason?: string | null;
}

/** consent.changed, and visit.state.consentState: the latest consent change and its chain entry id. */
export interface ConsentState {
  state: "given" | "withdrawn";
  at: string;
  by: ConsentBy;
  noticeId: string;
  noticeVersion: string;
  language: PatientLanguage;
  entryId: string;
}

export type RefusedReason =
  | "consent_required"
  | "consent_already_given"
  | "consent_not_given"
  | "wrong_notice"
  | "wrong_language"
  | "not_allowed"
  | "not_found"
  | "not_current"
  | "busy"
  | "invalid";

/** command.refused, only to the review connection that sent the command; no free text. */
export interface CommandRefused {
  command: string;
  reason: RefusedReason;
}

// ---------- CDR-006: record entries and interpreter dismissal ----------

export type DismissReason = "declined" | "resolved" | "simulated_call_ended";

/** interpreter.dismiss, controller only. */
export interface InterpreterDismiss {
  reason: DismissReason;
}

/** interpreter.dismissed, every role: the offer or request ended, so every screen clears it. */
export interface InterpreterDismissed {
  reason: DismissReason;
  at: string;
  entryId: string;
}

/** An interpreter offer, request, high-risk mark, or dismissal, as recorded; controller only. */
export interface EscalationEntry {
  entryId: string;
  action: "offer" | "request" | "mark" | "dismiss";
  reason: EscalationReason | DismissReason;
  at: string;
  turnId?: string | null;
  note?: string | null;
}

/** visit.state.injection, controller only (TDM-002): armed or idle, and the turns the mismatch fired on. */
export interface InjectionStatus {
  state: "idle" | "armed";
  injectedTurnIds: string[];
}

// ---------- CDR-006: review corrections, confirmations, and the tamper control ----------

/** A segment's version: "original", or the amendmentId of an applied correction. */
export type SegmentVersion = string;

export type CaptionCriticalValue = { kind: string; source: string; translated: string };

/** segment.confirm, review only: confirm the named version, which must still be current. */
export interface SegmentConfirm {
  segmentId: string;
  version: SegmentVersion;
}

/** segment.amend, review only: the recognised text (1 to 1000 characters) of the patient re-speaking their turn. */
export interface SegmentAmend {
  segmentId: string;
  text: string;
  language: PatientLanguage;
  recognitionConfidence: number;
}

export const SEGMENT_TEXT_MAX = 1000;

/** segment.status, every role: one stage of a correction, or its outcome; never any text. */
export interface SegmentStatus {
  segmentId: string;
  amendmentId: string;
  stage: "translating" | "verifying" | "retrying" | "applied" | "refused";
  reason?: "blocked" | "escalated" | "failed" | null;
}

/** segment.analysis, controller only: a correction's full turn graph result (result.turnId is the amendmentId). */
export interface SegmentAnalysis {
  segmentId: string;
  amendmentId: string;
  result: TurnResult;
}

/**
 * segment.amended, every role (CDR-001, extended by CDR-006): a correction applied or a confirmation recorded.
 * For "amend", newText, amendmentId, translation, and entryId are set; for "confirm", version and entryId.
 */
export interface SegmentAmended {
  segmentId: string;
  by: "patient" | "physician";
  action: "confirm" | "amend";
  newText?: string | null;
  amendmentId?: string | null;
  version?: SegmentVersion | null;
  translation?: string | null;
  toneLabel?: ToneLabel | null;
  criticalValues?: CaptionCriticalValue[] | null;
  entryId?: string | null;
}

/** One applied correction in a segment's history, as every role sees it. */
export interface SegmentAmendment {
  amendmentId: string;
  sourceText: string;
  translation: string;
  toneLabel: ToneLabel;
  criticalValues: CaptionCriticalValue[];
  at: string;
  entryId: string;
}

/** One applied correction with its full turn graph result: controller only. */
export interface SegmentAmendmentWithAnalysis extends SegmentAmendment {
  analysis: TurnResult;
}

export interface SegmentConfirmation {
  version: SegmentVersion;
  at: string;
  entryId: string;
}

/** visit.state.segments, every role: a turn with a confirmation or a correction, original first. */
export interface SegmentHistory {
  segmentId: string;
  original: TurnCaption;
  amendments: SegmentAmendment[];
  confirmed: SegmentConfirmation | null;
  current: SegmentVersion;
}

/** visit.state.segments for the controller: each amendment carries its analysis. */
export interface SegmentHistoryController extends SegmentHistory {
  amendments: SegmentAmendmentWithAnalysis[];
}

/** demo.tamper_record, controller only (TDM-005): alter one turn or amendment entry, once per visit. */
export interface TamperRecord {
  entryId: string;
}

/** demo.tamper_state, and visit.state.tamper, controller only (TDM-005): the entry the control altered. */
export interface TamperState {
  entryId: string;
  at: string;
}

// ---------- CDR-005: explain-back ----------

/** explainback.check and explainback.cancel, controller only. explainback.start takes an empty payload. */
export interface ExplainBackRef {
  explainBackId: string;
}

/** explainback.state, and visit.state.explainBack, every role: no text, items, or outcomes. */
export interface ExplainBackState {
  explainBackId: string;
  state: "listening" | "checking" | "done" | "failed" | "cancelled";
  explanationTurnIds: string[];
}

export type ExplainBackOutcome = "matched" | "missed" | "contradicted";

export interface ExplainBackItem {
  itemId: string;
  kind: "dose" | "frequency" | "medication" | "number" | "date" | "instruction" | "warning" | "follow_up";
  instruction: string;
  sourceTurnIds: string[];
  outcome: ExplainBackOutcome;
  decidedBy: "code" | "model";
  expected?: string | null;
  heard?: string | null;
  evidenceTurnIds: string[];
}

/** explainback.result, and visit.state.explainBackResults, controller only. */
export interface ExplainBackResult {
  explainBackId: string;
  planHeadHash: string;
  explanationTurnIds: string[];
  items: ExplainBackItem[];
  entryId: string;
}

// ---------- CDR-007: clinical note and patient summary ----------

/** note.status (controller only) and summary.status (every role); detail reaches controllers only. */
export interface ArtefactStatus {
  artefactId: string;
  kind: "note" | "summary";
  stage: "generating" | "checking" | "retrying" | "ready" | "failed" | "refused";
  detail?: string | null;
}

/** A cited source: a turn at its frozen effective version, or an interpreter line ("original"). */
export interface SourceRef {
  kind: "turn" | "interpreter_line";
  id: string;
  version: SegmentVersion;
}

export type ProvenanceTag =
  | "patient_stated"
  | "physician_stated"
  | "companion_stated"
  | "interpreter_stated"
  | "ai_inference";

export type NoteHeading = "Presenting complaint" | "History" | "Assessment" | "Plan" | "Follow-up";

export interface NoteSentence {
  sentenceId: string;
  text: string;
  tag: ProvenanceTag;
  sources: SourceRef[];
}

export interface NoteSection {
  heading: NoteHeading;
  sentences: NoteSentence[];
}

export interface TagDowngrade {
  sentenceId: string;
  from: ProvenanceTag;
  to: "ai_inference";
}

/** note.ready, and visit.state.note, controller only: a checked draft the physician remains author of. */
export interface ClinicalNote {
  noteId: string;
  language: "en-CA";
  basedOnHead: string;
  generatedAt: string;
  sections: NoteSection[];
  untranslatedTurnIds: string[];
  tagDowngrades: TagDowngrade[];
}

/** One summary sentence; its sentenceId is also its speech id, `{summaryId}.{index}`. */
export interface SummarySentence {
  sentenceId: string;
  index: number;
  text: string;
  sources: SourceRef[];
}

/** summary.ready, and visit.state.summary, every role: only ever a summary that passed its value check. */
export interface PatientSummary {
  summaryId: string;
  language: PatientLanguage;
  basedOnHead: string;
  generatedAt: string;
  sentences: SummarySentence[];
  values: { kind: CriticalKind; text: string; sourceTurnId: string }[];
  check: "passed";
}

export interface SummaryMismatch {
  kind: CriticalKind;
  expected: string;
  found: string | null;
  sourceTurnId: string | null;
  problem: "changed" | "missing" | "unsupported";
}

/** summary.check, and visit.state.summaryChecks, controller only: every check outcome and the values compared. */
export interface SummaryCheck {
  summaryId: string;
  attempt: 1 | 2;
  outcome: "passed" | "failed";
  mismatches: SummaryMismatch[];
}

/** summary.read_aloud and summary.stop, from review or the controller; a screen's copy is dropped. */
export interface SummaryRef {
  summaryId: string;
}

/** summary.speak, controller only: play the sentence ids in order (each through the speak gate), or stop. */
export interface SummarySpeak {
  summaryId: string;
  action: "play" | "stop";
  speechIds: string[];
}

/** artefacts.stale, every role: the chain grew after the current note or summary; note is false for screens. */
export interface ArtefactsStale {
  note: boolean;
  summary: boolean;
  headHash: string;
}
