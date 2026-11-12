"use client";

/**
 * Physician controller: languages, names, push-to-talk, hands-free listening, typed fallback, read-back, nudges,
 * explain-back, the note and summary, the presenter controls, turns, and latency.
 *
 * @implements IDR-001: Push-to-talk per speaker instead of diarisation
 * @implements IDR-004: Hands-free continuous listening, with the speaker found by spoken language
 * @implements ADR-003: Human interpreter escalation on low confidence and high-risk moments
 * @implements CDR-001: Visit WebSocket event contract
 * @implements CDR-002: Turn result schema
 * @implements CDR-003: Participant names and interpreter lines on the visit channel
 * @implements CDR-004: Interpreter voice playback on the visit channel
 * @implements TDM-003: Sinhala and Tamil as test-only languages before demo night
 * @implements TDM-002: Presenter mismatch control for the blocked-dose beat
 * @implements CDR-005: Consent and explain-back on the visit channel
 * @implements CDR-006: Record chain entries, review corrections, interpreter dismissal, and presenter controls
 * @implements IDR-003: SHA-256 hash chain for the record-verified badge
 * @implements CDR-007: Clinical note with provenance and patient summary on the visit channel
 * @implements TDM-005: Hidden record-tamper control for the demo
 * @implements MDD-005: Trust across the barrier
 * @implements CDR-008: Patient signals, manner, trust updates, companion turns, and the closing check on the visit channel
 * @implements IDR-005: Manner vocabulary and voice delivery
 * @implements ADR-012: Clinic design system
 * @contract ws:/ws/visit
 */

import { useCallback, useEffect, useEffectEvent, useRef, useState } from "react";
import type {
  ArtefactsStale,
  ArtefactStatus,
  ClinicalNote,
  ConsentNotice,
  ConsentSpeak,
  ConsentState,
  DemoInjectionState,
  DismissReason,
  Emotion,
  EmpathyNudge,
  Envelope,
  ErrorPayload,
  EscalationEntry,
  EscalationReason,
  ExplainBackResult,
  ExplainBackState,
  InterpreterDismissed,
  InterpreterEscalation,
  InterpreterLine,
  IntroductionState,
  Language,
  Manner,
  NameProposed,
  NameRole,
  Names,
  PatientLanguage,
  PatientSignal,
  PatientSignalEntry,
  PatientSummary,
  RecordIntegrity,
  SegmentAmended,
  SegmentHistory,
  Speaker,
  SummaryCheck,
  SummarySpeak,
  TamperState,
  TrustUpdate,
  TurnCaption,
  TurnRef,
  TurnResult,
  TurnStarted,
  TurnStatus,
  VisitStateController,
} from "@/lib/contracts";
import { NAME_MAX } from "@/lib/contracts";
import { INTERPRETER_CONNECTING_MS, INTERPRETER_SIMULATED_MS, type InterpreterPhase } from "@/lib/i18n";
import { LANGUAGE_LABELS, RECOGNITION, ROADMAP } from "@/lib/languages";
import { type ListeningState, type Side, VOICE_TAIL_MS, isShortReply, listeningState, sideFor } from "@/lib/listening";
import { type LatencyRow, median, segments as latencySegments, toCsv } from "@/lib/latency";
import { serverHttpUrl, useVisitSocket } from "@/lib/socket";
import {
  applyAmended,
  brokenEntryLabel,
  captionOf,
  effective,
  isConfirmed,
  summaryIndexOf,
  summaryReading,
  turnOfEntry,
  visitChanged,
} from "@/lib/record";
import { playbackMessages } from "@/lib/speaking";
import { insertTrust, lastSpokenIn, settledOrder } from "@/lib/trust";
import {
  type Capture,
  type Heard,
  type Listening,
  SpeechStopped,
  current,
  onSpeaking,
  speak,
  startCapture,
  startListening,
  stopSpeaking,
  warmUp,
} from "@/lib/speech";
import styles from "./controller.module.css";
import ExplainBackPanel from "./ExplainBackPanel";
import Highlighted from "./Highlighted";
import NoteSummaryPanel from "./NoteSummaryPanel";
import RecordBadge from "./RecordBadge";

// The physician's name, saved once on a clinic device so no visit has to ask for it (CDR-003).
const DEFAULT_NAME_KEY = "interpreter.defaultPhysicianName";

function readDefaultName(): string {
  try {
    return localStorage.getItem(DEFAULT_NAME_KEY) ?? "";
  } catch {
    return ""; // storage blocked: no default, the introduction asks instead
  }
}

function writeDefaultName(name: string) {
  try {
    if (name) localStorage.setItem(DEFAULT_NAME_KEY, name);
    else localStorage.removeItem(DEFAULT_NAME_KEY);
  } catch {
    // storage blocked: the name still applies to this visit
  }
}

const ASKING: Partial<Record<IntroductionState, NameRole>> = { asking_physician: "physician", asking_patient: "patient" };

const LISTENING_TEXT: Record<ListeningState, string> = {
  listening: "Listening",
  voice: "Paused while the interpreter speaks",
  readback: "Paused for the dose read-back",
  pushToTalk: "Paused while you hold a speaker",
};

const REASON_TEXT: Record<EscalationReason, string> = {
  low_confidence: "the translation stayed uncertain after a retry",
  tone_failure: "the tone check failed after a retry",
  high_risk: "this moment was marked high risk",
  requested: "an interpreter was requested",
};

const INTERPRETER_TEXT: Record<InterpreterPhase, string> = {
  offered: "A human interpreter is offered on the shared screen.",
  connecting: "Connecting to a human interpreter.",
  simulated: "Interpreter would join here (simulated). The consultation continues.",
};

const INJECTION_TEXT: Record<DemoInjectionState["state"], string> = {
  armed: "Armed: the next physician dose will be multiplied by 10 in translation, so it is blocked.",
  fired: "Fired on the turn marked in the log. Ask the physician to repeat the dose.",
  cancelled: "Cancelled before it fired. Doses are translated normally.",
};

/** Each recorded interpreter event (CDR-006), as the controller lists it. */
const ESCALATION_TEXT: Record<EscalationEntry["action"], string> = {
  offer: "Interpreter offered",
  request: "Interpreter requested",
  mark: "Marked high risk",
  dismiss: "Offer closed",
};

const DISMISS_TEXT: Record<DismissReason, string> = {
  declined: "declined",
  resolved: "resolved",
  simulated_call_ended: "simulated call ended",
};

const ACTION_FOR: Record<EscalationReason, EscalationEntry["action"]> = {
  low_confidence: "offer",
  tone_failure: "offer",
  high_risk: "mark",
  requested: "request",
};

const SPEAKER_TEXT: Record<Speaker, string> = { physician: "Physician", patient: "Patient", companion: "Companion" };

/** ADR-006, ADR-010: what the running server uses, from GET /api/health; every value is a string. */
type Services = {
  translator: string;
  liveModel: string;
  toneModel: string;
  recordModel: string;
  recognition: string;
  voice: string;
  voiceModel: string;
  voiceId: string;
  embeddings: string;
};

/** Display names for the model ids the server reports; an id not listed here is shown as it is. */
const MODEL_NAMES: Record<string, string> = {
  "claude-sonnet-5-5": "Claude Sonnet 5.5",
  "claude-haiku-5-5": "Haiku 5.5",
  "claude-opus-5-5": "Opus 5.5",
  eleven_v4: "Eleven v4",
};
const modelName = (id: string) => MODEL_NAMES[id] ?? id;

/**
 * The header's services line, so the presenter can see at a glance whether this is a live run.
 * @implements ADR-006: LLM: Claude Sonnet 5.5 for live turns, Opus 5.5 for note and summary
 * @implements ADR-010: Voice output: ElevenLabs Eleven v4 replaces OpenAI text-to-speech; Azure stays fallback
 */
function ServicesLine({ services }: { services: Services }) {
  const recognised = services.recognition === "azure";
  const recognition = recognised ? "Azure recognition." : "No speech recognition key.";
  let voice = "No voice.";
  if (services.voice === "elevenlabs") {
    voice = `ElevenLabs ${modelName(services.voiceModel)} voice${recognised ? ", Azure fallback" : ""}.`;
  } else if (services.voice === "azure") voice = "Azure voice.";
  return (
    <p className={styles.services} data-testid="services">
      {services.translator === "claude" ? (
        `${modelName(services.liveModel)} for turns, ${modelName(services.toneModel)} for checks, ` +
        `${modelName(services.recordModel)} for the note and summary.`
      ) : (
        <span className={styles.servicesWarn} data-state="fake">
          Fake model, no AI calls. Not for a live visit.
        </span>
      )}{" "}
      {recognition} {voice}
      {services.embeddings === "hashing" && (
        <>
          {" "}
          <span className={styles.servicesWarn}>Test embedder, not for rehearsal.</span>
        </>
      )}
    </p>
  );
}

/** CDR-008 trust view: the patient's or companion's emotion in plain words. */
const EMOTION_TEXT: Record<Emotion, string> = {
  calm: "sounds calm",
  worried: "sounds worried",
  embarrassed: "sounds embarrassed",
  in_pain: "sounds in pain",
  relieved: "sounds relieved",
  confused: "sounds confused",
};

/** IDR-005: the physician's manner in plain words, as read from what they said. */
const MANNER_TEXT: Record<Manner, string> = {
  plain: "said plainly",
  warm: "said warmly",
  reassuring: "said with reassurance",
  gentle: "said gently",
  serious: "said seriously",
  urgent: "said urgently",
  apologetic: "said with an apology",
  encouraging: "said with encouragement",
};

/** CDR-008: each patient signal as the trust view lists it. */
const SIGNAL_TEXT: Record<PatientSignal, string> = {
  not_understood: "Patient: did not understand",
  slower: "Patient: asked for slower",
  repeat: "Patient: asked to hear it again",
};

/** The three speakers the controller captures for, in the order of their keys (1, 2, 3). */
const TALK_SPEAKERS: Speaker[] = ["physician", "patient", "companion"];

/** A time of day for the record lists: hours and minutes, in the laptop's locale. */
function clock(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

/** An interpreter request or high-risk mark in the turn log, after the turn it followed (null: before any). */
interface Marker {
  id: number;
  reason: "high_risk" | "requested";
  after: string | null;
}

/** What happened to a turn after its analysis, as far as this controller saw it live. */
interface Outcome {
  spoken?: boolean;
  // The turn passed its checks but the voice failed, so the patient never heard it.
  voiceFailed?: boolean;
  discarded?: boolean;
  escalation?: EscalationReason;
}

function ValuesTable({ turn, only }: { turn: TurnResult; only?: "mismatched" }) {
  const rows = only ? turn.criticalValues.filter((v) => !v.matched) : turn.criticalValues;
  return (
    <table className={styles.values}>
      <thead>
        <tr>
          <th scope="col">Value</th>
          <th scope="col">{LANGUAGE_LABELS[turn.sourceLanguage].english} (said)</th>
          <th scope="col">{LANGUAGE_LABELS[turn.targetLanguage].english} (translation)</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((v, i) => (
          <tr key={i} className={v.matched ? undefined : styles.mismatch}>
            <td>{v.kind}</td>
            <td lang={turn.sourceLanguage}>{v.source || <em>not said</em>}</td>
            <td lang={turn.targetLanguage}>{v.translated || <em>missing</em>}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function statusText(turn: TurnResult, outcome: Outcome, pending: boolean): string {
  switch (turn.status) {
    case "final":
      return outcome.voiceFailed ? "voice failed, not spoken" : "spoken";
    case "blocked":
      return "blocked, not spoken";
    case "escalated":
      return "escalated, not spoken";
    case "readback_required":
      if (pending) return "waiting for your read-back";
      if (outcome.spoken) return outcome.voiceFailed ? "confirmed, voice failed" : "confirmed and spoken";
      if (outcome.discarded) return "rejected, not spoken";
      return "read-back closed";
  }
}

export default function Controller() {
  const [patientLanguage, setPatientLanguage] = useState<PatientLanguage>("pa-IN");
  const [turns, setTurns] = useState<TurnResult[]>([]);
  const [pendingReadback, setPendingReadback] = useState<string | null>(null);
  const [outcomes, setOutcomes] = useState<Record<string, Outcome>>({});
  const [nudges, setNudges] = useState<EmpathyNudge[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [latency, setLatency] = useState<LatencyRow[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [recording, setRecording] = useState<Speaker | null>(null);
  const [typedSpeaker, setTypedSpeaker] = useState<Speaker>("patient");
  const [typedText, setTypedText] = useState("");
  const [visitId, setVisitId] = useState<string | null>(null);
  const [names, setNames] = useState<Names>({ physicianName: null, patientName: null });
  const [physicianDraft, setPhysicianDraft] = useState("");
  const [patientDraft, setPatientDraft] = useState("");
  const [defaultName, setDefaultName] = useState("");
  const defaultAppliedTo = useRef<string | null>(null);
  // The names the server last sent: a field changes only when its own name did, never mid-typing.
  const serverNames = useRef<Names>({});
  const [introduction, setIntroduction] = useState<IntroductionState>("pending");
  const [proposed, setProposed] = useState<NameProposed | null>(null);
  const [introSkipped, setIntroSkipped] = useState(false);
  // TDM-003: chosen when the server starts and fixed until it restarts, so it is read once.
  const [testMode, setTestMode] = useState(false);
  // ADR-006, ADR-010: null until the health call answers, so the services line never guesses.
  const [services, setServices] = useState<Services | null>(null);
  const capture = useRef<Capture | null>(null);
  // IDR-004: hands-free listening, the side heard last, short replies waiting for the physician, and
  // whether the interpreter's voice (or its echo) is still in the room.
  const [handsFree, setHandsFree] = useState(false);
  const [lastHeard, setLastHeard] = useState<Side | null>(null);
  const [held, setHeld] = useState<(Heard & { id: number })[]>([]);
  const [voiceAudible, setVoiceAudible] = useState(false);
  const listening = useRef<Listening | null>(null);
  const muted = useRef(false);
  const heldIds = useRef(0);
  // Submits are sequential from this one controller, so turn.started events match them in order.
  const pendingTimes = useRef<{ endOfSpeechAt: number; submittedAt: number }[]>([]);
  // Off the record (CDR-001 visit.paused): nothing is captured, so speaking and sending are switched off.
  const [paused, setPaused] = useState(false);
  // ADR-003: the interpreter offer and the simulated call, timed exactly as on the shared screen.
  const [interpreter, setInterpreter] = useState<{ phase: InterpreterPhase; reason: EscalationReason } | null>(null);
  const callTimers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const [markers, setMarkers] = useState<Marker[]>([]);
  const markerIds = useRef(0);
  // TDM-002: the presenter's mismatch control, and the turns it fired on (marked here and nowhere public).
  const [injection, setInjection] = useState<DemoInjectionState["state"] | null>(null);
  const [injected, setInjected] = useState<Set<string>>(new Set());
  const lastStarted = useRef<string | null>(null);
  const lastTurn = useRef<string | null>(null);
  // CDR-005: the notice in the patient's language and English, and the latest consent change.
  const [consentNotice, setConsentNotice] = useState<ConsentNotice | null>(null);
  const [consentState, setConsentState] = useState<ConsentState | null>(null);
  const noticeRef = useRef<ConsentNotice | null>(null);
  // CDR-006: the record's integrity, every interpreter event as recorded, and whether an offer is open.
  const [integrity, setIntegrity] = useState<RecordIntegrity | null>(null);
  const [escalations, setEscalations] = useState<EscalationEntry[]>([]);
  const interpreterOpen = useRef(false);
  // CDR-005: the latest explain-back's state, and every result (private to the physician).
  const [explainBack, setExplainBack] = useState<ExplainBackState | null>(null);
  const [explainBackResults, setExplainBackResults] = useState<ExplainBackResult[]>([]);
  // CDR-006: corrections and confirmations from the review screen; TDM-005: the entry the tamper control altered.
  const [segments, setSegments] = useState<SegmentHistory[]>([]);
  const [tamper, setTamper] = useState<TamperState | null>(null);
  const turnsRef = useRef<TurnResult[]>([]);
  // CDR-007: the note (read in /record) and the summary, with their progress, checks, and stale flags.
  const [note, setNote] = useState<ClinicalNote | null>(null);
  const [noteStale, setNoteStale] = useState(false);
  const [noteStatus, setNoteStatus] = useState<ArtefactStatus | null>(null);
  const [summary, setSummary] = useState<PatientSummary | null>(null);
  const [summaryStale, setSummaryStale] = useState(false);
  const [summaryStatus, setSummaryStatus] = useState<ArtefactStatus | null>(null);
  const [summaryChecks, setSummaryChecks] = useState<SummaryCheck[]>([]);
  const summaryRef = useRef<PatientSummary | null>(null);
  const [tamperTarget, setTamperTarget] = useState("");
  // CDR-008: the private trust timeline, oldest first, and the last translation spoken in the patient's language,
  // so "say that again" can play it once more through the speak gate without a new turn.
  const [trust, setTrust] = useState<TrustUpdate[]>([]);
  const lastSpoken = useRef<{ text: string; language: Language; speechId: string } | null>(null);
  // CDR-008: settled turns in the order they settled, so a late trust update is listed at its turn's place.
  const settled = useRef<string[]>([]);
  // CDR-001 `visit.new`: the visit shown, the turn still in the graph (from turn.started until its analysis or
  // discard; nothing new can start while it runs), and whether the physician is confirming a new visit.
  const shownVisit = useRef<string | null>(null);
  const [inGraph, setInGraph] = useState<string | null>(null);
  const [confirmingNew, setConfirmingNew] = useState(false);

  const physicianLanguage: Language = "en-CA";
  const languageOf = (speaker: Speaker): Language => (speaker === "physician" ? physicianLanguage : patientLanguage);

  const updateLatency = (turnId: string, patch: Partial<LatencyRow>) =>
    setLatency((rows) => rows.map((r) => (r.turnId === turnId ? { ...r, ...patch } : r)));
  const updateOutcome = (turnId: string, patch: Outcome) =>
    setOutcomes((all) => ({ ...all, [turnId]: { ...all[turnId], ...patch } }));

  // The simulated call ends by closing the request on the server, so the TV and the record agree (CDR-006).
  // The channel's send, for timers set up before the socket hook in this component.
  const sendRef = useRef<(type: string, payload: unknown) => void>(() => {});
  // Refs and state setters only, so each is stable and the event handler below can use them.
  const startCall = useCallback(() => {
    callTimers.current.forEach(clearTimeout);
    setInterpreter({ phase: "connecting", reason: "requested" });
    const endCall = () => {
      callTimers.current = [];
      setInterpreter(null);
      if (interpreterOpen.current) sendRef.current("interpreter.dismiss", { reason: "simulated_call_ended" });
    };
    callTimers.current = [
      setTimeout(() => setInterpreter({ phase: "simulated", reason: "requested" }), INTERPRETER_CONNECTING_MS),
      setTimeout(endCall, INTERPRETER_CONNECTING_MS + INTERPRETER_SIMULATED_MS),
    ];
  }, []);

  const closeInterpreter = useCallback(() => {
    callTimers.current.forEach(clearTimeout);
    callTimers.current = [];
    setInterpreter(null);
  }, []);

  useEffect(() => () => callTimers.current.forEach(clearTimeout), []);

  const receiveNames = (current: Names) => {
    const last = serverNames.current;
    if (current.physicianName !== last.physicianName) setPhysicianDraft(current.physicianName ?? "");
    if (current.patientName !== last.patientName) setPatientDraft(current.patientName ?? "");
    serverNames.current = current;
    setNames(current);
  };

  // A voice that fails is reported; one stopped on purpose (a new visit, CDR-001; summary.stop) is not.
  const notSpoken = useCallback((error: Error) => {
    if (!(error instanceof SpeechStopped)) setNotice(`Not spoken: ${error.message}`);
  }, []);

  const onEvent = useCallback((event: Envelope) => {
    switch (event.type) {
      case "visit.state": {
        const state = event.payload as VisitStateController;
        if (visitChanged(shownVisit, event.visitId)) {
          // CDR-001 `visit.new`: everything kept only from live events goes, as if the page had just connected;
          // the snapshot below sets the rest. The saved default physician name is applied again for the new visit.
          stopSpeaking(() => true);
          const active = capture.current;
          capture.current = null;
          void active?.stop().catch(() => undefined);
          setRecording(null);
          setTypedText("");
          setOutcomes({});
          setDismissed(new Set());
          setLatency([]);
          pendingTimes.current = [];
          setProposed(null);
          setIntroSkipped(false);
          setHandsFree(false);
          setLastHeard(null);
          setHeld([]);
          setMarkers([]);
          setInjection(null);
          lastStarted.current = null;
          setNoteStatus(null);
          setSummaryStatus(null);
          setTamperTarget("");
          setInGraph(null);
          setConfirmingNew(false);
          setNotice("New visit started");
        }
        setPatientLanguage(state.patientLanguage);
        setTurns(state.turns);
        setPendingReadback(state.pendingReadback ?? null);
        setNudges(state.nudges);
        setVisitId(event.visitId);
        // Read here, not on first render: the page is also rendered on the server, which has no storage.
        setDefaultName(readDefaultName());
        receiveNames({ physicianName: state.physicianName ?? null, patientName: state.patientName ?? null });
        setIntroduction(state.introduction ?? "pending");
        setPaused(state.paused);
        lastTurn.current = state.turns.at(-1)?.turnId ?? null;
        noticeRef.current = state.consentNotice ?? null;
        setConsentNotice(state.consentNotice ?? null);
        setConsentState(state.consentState ?? null);
        setIntegrity(state.integrity);
        // CDR-006: a reload keeps the recorded interpreter events, the open offer, and the injection marks.
        const recorded = state.escalations ?? [];
        setEscalations(recorded);
        interpreterOpen.current = Boolean(state.interpreterOpen);
        if (!state.interpreterOpen) closeInterpreter();
        else {
          const last = recorded.findLast((e) => e.action !== "dismiss");
          // A call already running here keeps its timers; only a reload starts the simulated call again.
          if (last?.action === "request") {
            if (!callTimers.current.length) startCall();
          } else if (last) {
            const reason = (last.action === "mark" ? "high_risk" : last.reason) as EscalationReason;
            setInterpreter((current) => current ?? { phase: "offered", reason });
          }
        }
        if (state.injection) {
          setInjected(new Set(state.injection.injectedTurnIds));
          setInjection((current) => (state.injection?.state === "armed" ? "armed" : current === "armed" ? null : current));
        }
        turnsRef.current = state.turns;
        setExplainBack(state.explainBack ?? null);
        setExplainBackResults(state.explainBackResults ?? []);
        setSegments(state.segments ?? []);
        setTamper(state.tamper ?? null);
        setNote(state.note ?? null);
        setNoteStale(Boolean(state.noteStale));
        summaryRef.current = state.summary ?? null;
        setSummary(state.summary ?? null);
        setSummaryStale(Boolean(state.summaryStale));
        setSummaryChecks(state.summaryChecks ?? []);
        const trustList = state.trust ?? [];
        setTrust(trustList);
        // CDR-008: a reloaded controller still knows the turn order and what was last said to the patient.
        settled.current = settledOrder(state.turns, trustList, state.pendingReadback ?? null);
        lastSpoken.current = lastSpokenIn(state.turns, trustList, settled.current, state.patientLanguage);
        break;
      }
      case "trust.update": {
        // CDR-008: controller only; one per settled turn and one per patient signal, never shown anywhere else.
        // A turn's update arrives when its advisor returns, so it is placed by spoken order, as the server keeps it.
        const update = event.payload as TrustUpdate;
        setTrust((all) => insertTrust(all, update, settled.current));
        break;
      }
      case "patient.signal": {
        // CDR-008: "say that again" replays the last spoken translation by its id, so the speak gate serves it
        // again and voice.started and voice.ended fire as for a normal relay.
        const entry = event.payload as PatientSignalEntry;
        if (entry.signal !== "repeat") break;
        const last = lastSpoken.current;
        if (!last) {
          setNotice("The patient asked to hear it again, but nothing spoken to them is known here. Say it again.");
          break;
        }
        speak(last.text, last.language, last.speechId).catch((error: Error) => {
          if (!(error instanceof SpeechStopped)) setNotice(`Not repeated: ${error.message}`);
        });
        break;
      }
      case "explainback.state":
        setExplainBack(event.payload as ExplainBackState);
        break;
      case "explainback.result": {
        const result = event.payload as ExplainBackResult;
        setExplainBackResults((all) => [...all.filter((r) => r.explainBackId !== result.explainBackId), result]);
        break;
      }
      case "segment.amended": {
        const amended = event.payload as SegmentAmended;
        setSegments((all) =>
          applyAmended(
            all,
            amended,
            (id) => {
              const turn = turnsRef.current.find((t) => t.turnId === id);
              return turn ? captionOf(turn) : null;
            },
            event.ts,
          ),
        );
        break;
      }
      case "demo.tamper_state":
        setTamper(event.payload as TamperState);
        break;
      case "note.status":
        setNoteStatus(event.payload as ArtefactStatus);
        break;
      case "note.ready":
        setNote(event.payload as ClinicalNote);
        setNoteStale(false);
        break;
      case "summary.status":
        setSummaryStatus(event.payload as ArtefactStatus);
        break;
      case "summary.check": {
        const check = event.payload as SummaryCheck;
        setSummaryChecks((all) => [...all, check]);
        break;
      }
      case "summary.ready": {
        const ready = event.payload as PatientSummary;
        summaryRef.current = ready;
        setSummary(ready);
        setSummaryStale(false);
        break;
      }
      case "artefacts.stale": {
        const stale = event.payload as ArtefactsStale;
        setNoteStale(stale.note);
        setSummaryStale(stale.summary);
        break;
      }
      case "summary.speak": {
        // CDR-007: the patient or physician asked; this controller is the only voice, a sentence at a time.
        const request = event.payload as SummarySpeak;
        if (request.action === "stop") {
          // A stop may name no sentences: it then stops every sentence of that summary.
          const named = new Set(request.speechIds);
          stopSpeaking((id) => named.has(id) || summaryIndexOf(request.summaryId, id) !== null);
          break;
        }
        const current = summaryRef.current;
        if (!current || current.summaryId !== request.summaryId) break;
        const texts = new Map(summaryReading(current).map((s) => [s.speechId, s.text]));
        for (const speechId of request.speechIds) {
          const text = texts.get(speechId);
          if (!text) continue;
          speak(text, current.language, speechId).catch((error: Error) => {
            if (!(error instanceof SpeechStopped)) setNotice(`Summary not spoken: ${error.message}`);
          });
        }
        break;
      }
      case "consent.changed": {
        const consent = event.payload as ConsentState;
        setConsentState(consent);
        if (consent.state === "withdrawn") {
          setHandsFree(false);
          setNotice("Consent withdrawn. Nothing is captured until it is given again.");
        } else setNotice(null);
        break;
      }
      case "consent.speak": {
        // CDR-005: the notice is read in the patient's language through the speak gate, by its speech id.
        const { speechId, language } = event.payload as ConsentSpeak;
        const text = noticeRef.current?.lines.find((line) => line.language === language)?.text;
        if (text) speak(text, language, speechId).catch(notSpoken);
        break;
      }
      case "record.integrity":
        setIntegrity(event.payload as RecordIntegrity);
        break;
      case "interpreter.dismissed": {
        const dismissed = event.payload as InterpreterDismissed;
        interpreterOpen.current = false;
        closeInterpreter();
        setEscalations((all) => [
          ...all,
          { entryId: dismissed.entryId, action: "dismiss", reason: dismissed.reason, at: dismissed.at },
        ]);
        break;
      }
      case "visit.paused":
        setPaused(true);
        break;
      case "visit.resumed":
        setPaused(false);
        break;
      case "demo.injection_state": {
        const { state } = event.payload as DemoInjectionState;
        setInjection(state);
        // Fired while the turn that carries it is being translated: the one started last.
        const turnId = lastStarted.current;
        if (state === "fired" && turnId) setInjected((all) => new Set(all).add(turnId));
        break;
      }
      case "interpreter.line": {
        const line = event.payload as InterpreterLine;
        // CDR-008: the closing check is spoken in the patient's language only; its English is shown here.
        const closing = line.purpose === "ask_if_clear";
        const spoken = closing ? line.lines.filter((l) => l.language !== physicianLanguage) : line.lines;
        // speak() keeps lines in order and fetches each one's audio straight away.
        for (const { language, text } of spoken) {
          speak(text, language, line.lineId).catch(notSpoken);
        }
        if (closing) {
          const english = line.lines.find((l) => l.language === physicianLanguage)?.text;
          if (english) setNotice(`Asked the patient: ${english}`);
        }
        break;
      }
      case "visit.name_proposed":
        setProposed(event.payload as NameProposed);
        break;
      case "visit.names": {
        receiveNames(event.payload as Names);
        setProposed(null);
        break;
      }
      case "turn.started": {
        const started = event.payload as TurnStarted;
        lastStarted.current = started.turnId;
        setInGraph(started.turnId);
        const now = Date.now();
        const times = pendingTimes.current.shift() ?? { endOfSpeechAt: now, submittedAt: now };
        setLatency((rows) => [...rows, { turnId: started.turnId, speaker: started.speaker, ...times }]);
        break;
      }
      case "turn.status": {
        const status = event.payload as TurnStatus;
        // A turn leaves the graph with its analysis, or here when it fails or is discarded on the way.
        if (status.stage === "discarded" || status.stage === "failed") {
          setInGraph((id) => (id === status.turnId ? null : id));
        }
        if (status.stage === "discarded") {
          updateOutcome(status.turnId, { discarded: true });
          setPendingReadback((p) => (p === status.turnId ? null : p));
          setNotice("Dose rejected and not spoken. Ask the physician to say it again.");
        }
        break;
      }
      case "turn.analysis": {
        const result = event.payload as TurnResult;
        setInGraph((id) => (id === result.turnId ? null : id));
        updateLatency(result.turnId, { analysisAt: Date.now() });
        setTurns((prev) => {
          const next = [...prev.filter((t) => t.turnId !== result.turnId), result];
          turnsRef.current = next;
          return next;
        });
        lastTurn.current = result.turnId;
        if (result.status === "blocked") {
          setNotice("Blocked: a value changed in translation. Ask the speaker to repeat or rephrase.");
        }
        break;
      }
      case "turn.readback_required":
        setPendingReadback((event.payload as TurnRef).turnId);
        break;
      case "turn.result": {
        const caption = event.payload as TurnCaption;
        // Every turn.result is a turn settling (spoken, blocked, or escalated), in the order the server settled it.
        if (!settled.current.includes(caption.turnId)) settled.current = [...settled.current, caption.turnId];
        updateLatency(caption.turnId, { resultAt: Date.now(), spoken: caption.status === "final" });
        // The public caption is the signal to speak (CDR-002: shown only once spoken).
        if (caption.status === "final" && caption.translation) {
          updateOutcome(caption.turnId, { spoken: true });
          setPendingReadback((p) => (p === caption.turnId ? null : p));
          if (caption.targetLanguage !== physicianLanguage) {
            lastSpoken.current = { text: caption.translation, language: caption.targetLanguage, speechId: caption.turnId };
          }
          speak(caption.translation, caption.targetLanguage, caption.turnId)
            .then(({ startedAt }) => updateLatency(caption.turnId, { speechStartAt: startedAt }))
            .catch((error: Error) => {
              // Stopped (a new visit, CDR-001) is not a failure of the voice.
              if (error instanceof SpeechStopped) return;
              updateOutcome(caption.turnId, { voiceFailed: true });
              setNotice(`Not spoken: ${error.message}`);
            });
        }
        break;
      }
      case "interpreter.escalation": {
        const { reason, turnId } = event.payload as InterpreterEscalation;
        // The server chained it; the live event carries no entry id, so this copy is keyed locally until a reload.
        interpreterOpen.current = true;
        setEscalations((all) => [
          ...all,
          { entryId: `live-${all.length}`, action: ACTION_FOR[reason], reason, at: new Date().toISOString(), turnId },
        ]);
        if (reason === "requested" || reason === "high_risk") {
          // Recorded in the visit by the server; shown in the log where it happened.
          const after = turnId ?? lastTurn.current;
          setMarkers((all) => [...all, { id: ++markerIds.current, reason, after }]);
        }
        if (reason === "requested") {
          startCall();
          break;
        }
        if (turnId) updateOutcome(turnId, { escalation: reason });
        setInterpreter((current) => (current && current.phase !== "offered" ? current : { phase: "offered", reason }));
        if (reason !== "high_risk") setNotice(`Not spoken: ${REASON_TEXT[reason]}. Offer a human interpreter.`);
        break;
      }
      case "empathy.nudge":
        setNudges((prev) => [...prev, event.payload as EmpathyNudge]);
        break;
      case "error": {
        const error = event.payload as ErrorPayload;
        // CDR-004: a refused start only means the screen will not show it; the voice itself is unaffected.
        if (error.command === "voice.started") console.warn(`voice.started refused: ${error.message}`);
        // Another controller may have closed the simulated call first; the offer is closed either way.
        else if (error.command === "interpreter.dismiss") console.warn(`interpreter.dismiss refused: ${error.message}`);
        else setNotice(error.message);
        break;
      }
    }
  }, [startCall, closeInterpreter, notSpoken, physicianLanguage]);

  const { state, send } = useVisitSocket("controller", onEvent);

  useEffect(() => {
    sendRef.current = send;
  }, [send]);

  const dismissInterpreter = (reason: DismissReason) => send("interpreter.dismiss", { reason });

  // CDR-005: consent is given to the current notice in the patient's language; the server is the gate.
  const consented = consentState?.state === "given";
  const giveConsent = () =>
    consentNotice &&
    send("consent.give", { noticeVersion: consentNotice.version, language: consentNotice.language });

  useEffect(() => {
    fetch(`${serverHttpUrl()}/api/health`)
      .then((response) => response.json())
      .then((health: { testLanguages?: boolean; services?: Services }) => {
        setTestMode(Boolean(health.testLanguages));
        setServices(health.services ?? null);
      })
      .catch(() => setTestMode(false)); // unreachable server: the safe answer is no test languages
  }, []);

  // Apply the saved default once per visit, so clearing the name mid-visit is not undone.
  useEffect(() => {
    if (state !== "open" || !visitId || !defaultName || defaultAppliedTo.current === visitId) return;
    defaultAppliedTo.current = visitId;
    if (!names.physicianName) send("visit.set_names", { physicianName: defaultName });
  }, [state, visitId, defaultName, names.physicianName, send]);

  const tidy = (draft: string) => draft.trim().replace(/\s+/g, " ");

  const commitName = (role: "physician" | "patient", draft: string) => {
    const name = tidy(draft);
    const key = role === "physician" ? "physicianName" : "patientName";
    if (name !== (names[key] ?? "")) send("visit.set_names", { [key]: name });
  };

  // Only this checkbox changes the saved default: a locum editing the name for one visit leaves it alone.
  const isDefault = Boolean(defaultName) && defaultName === tidy(physicianDraft);
  const toggleDefault = (save: boolean) => {
    const name = save ? tidy(physicianDraft) : "";
    writeDefaultName(name);
    setDefaultName(name);
  };

  // While the interpreter asks someone their name, what they say next is their reply, not a turn.
  const askingRole: NameRole | null = introSkipped ? null : (ASKING[introduction] ?? null);

  const submit = (speaker: Speaker, text: string, confidence: number, endOfSpeechAt: number) => {
    if (!consented) {
      // Heard before consent, or just as it was withdrawn: dropped here, and the server would refuse it anyway.
      setNotice("Consent is needed before the conversation starts.");
      return;
    }
    if (paused) {
      // Heard just as the pause began: dropped here, and the server would refuse it anyway.
      setNotice("Paused: nothing is recorded. Resume to continue.");
      return;
    }
    if (!text.trim()) {
      setNotice("Nothing was heard. Please try again.");
      return;
    }
    setNotice(null);
    if (speaker === askingRole) {
      setProposed(null);
      send("visit.name_reply", { role: speaker, text: text.trim() });
      return;
    }
    pendingTimes.current.push({ endOfSpeechAt, submittedAt: Date.now() });
    send("turn.submit", { speaker, language: languageOf(speaker), text: text.trim(), recognitionConfidence: confidence });
  };

  const pressTalk = async (speaker: Speaker) => {
    if (recording) return;
    if (!consented) {
      setNotice("Consent is needed before the conversation starts.");
      return;
    }
    if (paused) {
      setNotice("Paused: nothing is recorded. Resume to speak.");
      return;
    }
    setNotice(null);
    setRecording(speaker);
    try {
      capture.current = await startCapture(languageOf(speaker));
    } catch (error) {
      setRecording(null);
      setNotice(`Microphone or speech unavailable: ${(error as Error).message}. Use typed input.`);
    }
  };

  const releaseTalk = async () => {
    const speaker = recording;
    const active = capture.current;
    capture.current = null;
    setRecording(null);
    if (!speaker || !active) return;
    try {
      const heard = await active.stop();
      submit(speaker, heard.text, heard.confidence, heard.endOfSpeechAt);
    } catch (error) {
      const reason = (error as Error).message.replace(/[\s.]+$/, "");
      setNotice(`Speech recognition failed: ${reason}. Try again or use typed input.`);
    }
  };

  // CDR-004: tell the visit what the interpreter's voice is playing, so the shared screen can show it.
  useEffect(() => {
    let previous: ReturnType<typeof current> = null;
    return onSpeaking((next) => {
      for (const { type, payload } of playbackMessages(previous, next)) send(type, payload);
      previous = next;
    });
  }, [send]);

  // The server forgets the speech when this connection drops, so a reconnect mid-speech reports it again.
  useEffect(() => {
    const playing = current();
    if (state === "open" && playing) send("voice.started", playing);
  }, [state, send]);

  // Open the Azure voices for this visit's languages before the first turn, so speech starts at once.
  useEffect(() => {
    void warmUp([patientLanguage, physicianLanguage]);
  }, [patientLanguage]);

  const sides: Side[] = [
    { speaker: "physician", language: physicianLanguage, recognition: RECOGNITION[physicianLanguage] },
    { speaker: "patient", language: patientLanguage, recognition: RECOGNITION[patientLanguage] },
  ];

  // Each utterance goes to the side whose language it was heard in; short ones wait for the physician.
  const hear = useEffectEvent((heard: Heard) => {
    const side = sideFor(heard.recognition, sides);
    if (!side) return;
    if (isShortReply(heard.text)) {
      setHeld((queue) => [...queue, { ...heard, id: ++heldIds.current }]);
      return;
    }
    setLastHeard(side);
    submit(side.speaker, heard.text, heard.confidence, heard.endOfSpeechAt);
  });

  const listenFailed = useEffectEvent((message: string) => {
    setHandsFree(false);
    setNotice(`Hands-free stopped: ${message.replace(/[\s.]+$/, "")}. Use push-to-talk.`);
  });

  useEffect(() => {
    if (!handsFree) return;
    let stopped = false;
    let active: Listening | null = null;
    startListening(sides.map((side) => side.recognition), hear, listenFailed)
      .then((started) => {
        if (stopped) return void started.stop();
        active = started;
        listening.current = started;
        started.mute(muted.current); // the voice may already be playing when listening starts
      })
      .catch((error: Error) => listenFailed(error.message));
    return () => {
      stopped = true;
      listening.current = null;
      void active?.stop();
    };
    // Restart only when the mode or the patient's language changes; the handlers are effect events.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [handsFree, patientLanguage]);

  // The interpreter's voice, and a short tail for its echo, keep the microphone muted.
  useEffect(() => {
    let tail: ReturnType<typeof setTimeout> | undefined;
    const unsubscribe = onSpeaking((item) => {
      clearTimeout(tail);
      if (item) setVoiceAudible(true);
      else tail = setTimeout(() => setVoiceAudible(false), VOICE_TAIL_MS);
    });
    return () => {
      clearTimeout(tail);
      unsubscribe();
    };
  }, []);

  const listenState = listeningState({
    voice: voiceAudible,
    readback: pendingReadback !== null,
    pushToTalk: recording !== null,
  });

  // Off the record, hands-free hears nothing at all, not even to throw it away.
  useEffect(() => {
    muted.current = listenState !== "listening" || paused;
    listening.current?.mute(muted.current);
  }, [listenState, handsFree, paused]);

  const resolveHeld = (speaker: Speaker | null) => {
    const [first, ...rest] = held;
    if (!first) return;
    setHeld(rest);
    if (!speaker) return;
    setLastHeard(sides.find((side) => side.speaker === speaker) ?? null);
    submit(speaker, first.text, first.confidence, first.endOfSpeechAt);
  };

  // Hold 1 for the physician, 2 for the patient, and 3 for a companion; with a short reply waiting, 1 or 2 says
  // whose it was (a companion's reply is taken with the companion control, never from hands-free: IDR-004).
  useEffect(() => {
    const keyToSpeaker: Record<string, Speaker> = { "1": "physician", "2": "patient", "3": "companion" };
    const down = (e: KeyboardEvent) => {
      const speaker = keyToSpeaker[e.key];
      const focused = document.activeElement;
      const typing =
        focused instanceof HTMLTextAreaElement || (focused instanceof HTMLInputElement && focused.type === "text");
      if (!speaker || e.repeat || typing) return;
      if (held.length && speaker !== "companion") resolveHeld(speaker);
      else void pressTalk(speaker);
    };
    const up = (e: KeyboardEvent) => {
      if (keyToSpeaker[e.key]) void releaseTalk();
    };
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
    };
  });

  const sendTyped = () => {
    submit(typedSpeaker, typedText, 1, Date.now());
    setTypedText("");
  };

  const decideReadback = (turnId: string, confirmed: boolean) =>
    send(confirmed ? "turn.readback_confirm" : "turn.readback_reject", { turnId });

  const measured = latency.map(latencySegments).filter((s) => s.totalMs !== undefined);
  const medianMs = median(measured.map((s) => s.totalMs));
  const breakdown = [
    { label: "Recognition", ms: median(measured.map((s) => s.recognitionMs)) },
    { label: "Server", ms: median(measured.map((s) => s.serverMs)) },
    { label: "Voice start", ms: median(measured.map((s) => s.voiceMs)) },
  ];

  const downloadCsv = () => {
    const url = URL.createObjectURL(new Blob([toCsv(latency)], { type: "text/csv" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: "latency.csv" });
    a.click();
    URL.revokeObjectURL(url);
  };

  /** Interpreter requests and high-risk marks, in the log after the turn they followed. */
  const markersAfter = (turnId: string | null) =>
    markers
      .filter((m) => m.after === turnId)
      .map((m) => (
        <li key={`marker-${m.id}`} className={styles.marker} data-testid="marker" data-reason={m.reason}>
          <span className={styles.eyebrow}>
            {m.reason === "high_risk" ? "Marked high risk, interpreter offered" : "Human interpreter requested"}
          </span>
        </li>
      ));

  /** The entry record.integrity names as broken, in words: a turn by its number in the log, or what else it is. */
  const brokenAt = integrity?.status === "broken" ? (integrity.brokenAt ?? null) : null;
  const brokenWhere = brokenEntryLabel(
    brokenAt,
    turns.map((t) => t.turnId),
    segments,
    {
      consent: consentState ? [consentState.entryId] : [],
      interpreter: escalations.map((e) => e.entryId),
      explainBack: explainBackResults.map((r) => r.entryId),
      summary: summary ? [summary.summaryId] : [],
    },
  );
  // The turn a broken or tampered entry belongs to: the turn itself, or the turn a correction amends.
  const brokenTurnId = turnOfEntry(brokenAt, segments);
  const tamperedTurnId = turnOfEntry(tamper?.entryId, segments);
  // TDM-005: the entries the tamper control may alter: settled turns, and applied corrections.
  const tamperTargets = [
    ...turns
      .map((t, i) => ({ entryId: t.turnId, label: `Turn ${i + 1}, ${SPEAKER_TEXT[t.speaker]}: ${t.sourceText}` }))
      .filter((t) => t.entryId !== pendingReadback),
    ...segments.flatMap((h) =>
      h.amendments.map((a) => ({
        entryId: a.amendmentId,
        label: `Turn ${turns.findIndex((t) => t.turnId === h.segmentId) + 1} correction: ${a.sourceText}`,
      })),
    ),
  ];
  const target = tamperTargets.some((t) => t.entryId === tamperTarget) ? tamperTarget : (tamperTargets.at(-1)?.entryId ?? "");

  const readbackTurn = turns.find((t) => t.turnId === pendingReadback);
  const nudge = [...nudges].reverse().find((n) => !dismissed.has(n.turnId));

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Demo night interpreter</p>
          <h1>Physician controller</h1>
          {services && <ServicesLine services={services} />}
        </div>
        <div className={styles.headerStatus}>
          <RecordBadge integrity={integrity} where={brokenWhere} className={styles.badge} />
          <span className={`${styles.status} ${styles[state]}`} data-testid="connection">
            {state}
          </span>
        </div>
      </header>

      {testMode && (
        <p className={styles.testBanner} role="status" data-testid="test-mode-banner">
          Test mode: Sinhala can be selected for test scripts only. Restart without TEST_LANGUAGES before
          any stage use.
        </p>
      )}

      {/* Controls on the left; the turn log and latency, read rather than used, in a panel on the right. */}
      <div className={styles.layout}>
        <div className={styles.controls}>
          <section className={styles.section}>
            <h2 className={styles.eyebrow}>Visit</h2>
            <div className={styles.visit}>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>Patient language</span>
                <select
                  data-testid="patient-language"
                  value={patientLanguage}
                  disabled={turns.length > 0 || consented}
                  onChange={(e) =>
                    send("visit.set_languages", { patientLanguage: e.target.value, physicianLanguage: "en-CA" })
                  }
                >
                  {ROADMAP.map(({ own, english, language, test }) => {
                    const selectable = Boolean(language) && (!test || testMode);
                    let note = "";
                    if (english === "English") note = "physician";
                    else if (!selectable) note = "coming soon";
                    else if (test) note = "test only";
                    return (
                      <option key={english} value={language ?? english} disabled={!selectable}>
                        {own} ({english}){note && `, ${note}`}
                      </option>
                    );
                  })}
                </select>
              </label>
              <p className={styles.aside}>
                {consented ? "With English. Fixed while consent is given." : "With English. Fixed once the first turn starts."}
              </p>
            </div>
            <div className={styles.visit}>
              {(["physician", "patient"] as const).map((role) => {
                const draft = role === "physician" ? physicianDraft : patientDraft;
                const setDraft = role === "physician" ? setPhysicianDraft : setPatientDraft;
                return (
                  <label key={role} className={styles.field}>
                    <span className={styles.fieldLabel}>{role === "physician" ? "Physician name" : "Patient name"}</span>
                    <input
                      type="text"
                      data-testid={`name-${role}`}
                      value={draft}
                      maxLength={NAME_MAX}
                      autoComplete="off"
                      placeholder={role === "physician" ? "Dr. Thomas" : "Optional"}
                      onChange={(e) => setDraft(e.target.value)}
                      // Read the field itself: Enter can arrive before React re-renders with the last keystroke.
                      onBlur={(e) => commitName(role, e.currentTarget.value)}
                      onKeyDown={(e) => e.key === "Enter" && commitName(role, e.currentTarget.value)}
                    />
                  </label>
                );
              })}
              <label className={styles.check}>
                <input
                  type="checkbox"
                  data-testid="name-default"
                  checked={isDefault}
                  disabled={!isDefault && !tidy(physicianDraft)}
                  onChange={(e) => toggleDefault(e.target.checked)}
                />
                <span>Use this physician name for every visit on this device</span>
              </label>
              {defaultName && !isDefault && (
                <p className={styles.aside} data-testid="name-default-note">
                  Saved default: {defaultName}
                </p>
              )}
            </div>
            {/* CDR-005: consent comes before anyone speaks, the introduction included. */}
            <div
              className={styles.consent}
              data-testid="consent"
              data-state={consentState?.state ?? "none"}
              data-by={consented ? consentState?.by : undefined}
            >
              {consented && consentState ? (
                <div className={styles.consentGiven}>
                  <p className={styles.consentStatus} data-testid="consent-status">
                    {/* One flex item, so the gap after the dot never opens a space before the comma. */}
                    <span>
                      Consent given {clock(consentState.at)}
                      <span className={styles.consentBy}>
                        {consentState.by === "patient" ? ", by the patient" : ", on the patient’s behalf"}
                      </span>
                    </span>
                  </p>
                  <div className={styles.consentLinks}>
                    <button
                      className={styles.quiet}
                      data-testid="consent-read"
                      onClick={() => send("consent.read_aloud", {})}
                    >
                      Read notice again
                    </button>
                    <button className={styles.quiet} data-testid="consent-withdraw" onClick={() => send("consent.withdraw", {})}>
                      Withdraw consent
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <p className={styles.eyebrow}>
                    Consent
                    {consentState?.state === "withdrawn"
                      ? `: withdrawn ${clock(consentState.at)}, nothing is captured`
                      : ": needed before anyone speaks"}
                  </p>
                  {consentNotice ? (
                    <div className={styles.consentNotice} data-testid="consent-notice">
                      {consentNotice.lines.map(({ language, text }) => (
                        <p key={language} lang={language}>
                          {text}
                        </p>
                      ))}
                    </div>
                  ) : (
                    <p className={styles.aside}>No consent notice for this language.</p>
                  )}
                  <div className={styles.actions}>
                    <button
                      className={styles.primary}
                      data-testid="consent-give"
                      disabled={state !== "open" || !consentNotice}
                      onClick={giveConsent}
                    >
                      Patient agrees
                    </button>
                    <button
                      className={styles.secondary}
                      data-testid="consent-read"
                      disabled={state !== "open" || !consentNotice}
                      onClick={() => send("consent.read_aloud", {})}
                    >
                      Read notice aloud
                    </button>
                  </div>
                  <p className={styles.aside}>
                    Read it aloud, then press when the patient agrees. It is recorded as given on their behalf.
                  </p>
                </>
              )}
            </div>
            <div className={styles.intro} data-testid="introduction" data-state={introSkipped ? "skipped" : introduction}>
              {introduction === "pending" && turns.length === 0 && (
                <>
                  <button
                    className={styles.secondary}
                    data-testid="intro-start"
                    disabled={state !== "open" || !consented}
                    onClick={() => send("visit.start_introduction", {})}
                  >
                    Start introduction
                  </button>
                  <p className={styles.aside}>
                    {consented
                      ? "The interpreter greets you both and asks for any name it does not know."
                      : "The interpreter introduces itself once the patient agrees."}
                  </p>
                </>
              )}
              {introduction === "done" && turns.length === 0 && (
                <p className={styles.aside}>Introduction done. Every relay now uses these names.</p>
              )}
              {askingRole && !proposed && (
                <>
                  <p className={styles.introStatus}>
                    Asking the {askingRole} for their name. Hold {askingRole === "physician" ? "1" : "2"} to answer, or
                    type it above.
                  </p>
                  <button className={styles.quiet} data-testid="intro-skip" onClick={() => setIntroSkipped(true)}>
                    Skip and start the visit
                  </button>
                </>
              )}
              {askingRole && proposed && (
                <>
                  <p className={styles.introStatus} data-testid="intro-proposed">
                    Heard the {proposed.role}&rsquo;s name as <strong>{proposed.name}</strong>
                  </p>
                  <div className={styles.actions}>
                    <button
                      className={styles.primary}
                      data-testid="intro-confirm"
                      onClick={() => send("visit.name_confirm", { role: proposed.role })}
                    >
                      Use this name
                    </button>
                    <button
                      className={styles.secondary}
                      data-testid="intro-reject"
                      onClick={() => {
                        setProposed(null);
                        send("visit.name_reject", { role: proposed.role });
                      }}
                    >
                      Ask again
                    </button>
                  </div>
                </>
              )}
            </div>
            {/* CDR-001 `visit.new`: a fresh visit on every screen without restarting the server; asks first. */}
            {confirmingNew ? (
              <div className={styles.newVisitConfirm} role="group" aria-label="Start a new visit">
                <p className={styles.newVisitWarning}>This clears the current visit on every screen. The record is not kept.</p>
                <div className={styles.actions}>
                  <button
                    className={styles.danger}
                    data-testid="new-visit-confirm"
                    disabled={state !== "open" || inGraph !== null}
                    onClick={() => {
                      setConfirmingNew(false);
                      send("visit.new", {});
                    }}
                  >
                    Start new visit
                  </button>
                  <button className={styles.secondary} data-testid="new-visit-cancel" onClick={() => setConfirmingNew(false)}>
                    Keep this visit
                  </button>
                </div>
              </div>
            ) : (
              <div className={styles.actions}>
                <button
                  className={styles.secondary}
                  data-testid="new-visit"
                  disabled={state !== "open" || inGraph !== null}
                  title={inGraph !== null ? "Wait for the turn being interpreted to finish" : undefined}
                  onClick={() => setConfirmingNew(true)}
                >
                  Start a new visit
                </button>
              </div>
            )}
          </section>

          <section className={styles.section}>
            <div className={styles.speakHead}>
              <h2 className={styles.eyebrow}>Speak</h2>
              <label className={styles.check}>
                <input
                  type="checkbox"
                  data-testid="hands-free"
                  checked={handsFree}
                  disabled={!consented}
                  onChange={(e) => {
                    setHandsFree(e.target.checked);
                    setLastHeard(null);
                    setHeld([]);
                  }}
                />
                Hands-free
              </label>
            </div>
            {handsFree && (
              <p
                className={styles.listening}
                data-testid="listening"
                data-state={paused ? "paused" : listenState}
                aria-live="polite"
              >
                {paused ? "Paused: off the record" : LISTENING_TEXT[listenState]}
                {lastHeard && (
                  <span className={styles.lastHeard}>
                    , last heard {lastHeard.speaker}, {LANGUAGE_LABELS[lastHeard.language].own}
                  </span>
                )}
              </p>
            )}
            {held[0] && (
              <div className={styles.held} data-testid="held-reply" aria-live="assertive">
                <p className={styles.eyebrow}>Short reply: whose words were these?</p>
                <p className={styles.heldText} data-testid="held-text">
                  {held[0].text}
                </p>
                <div className={styles.actions}>
                  <button className={styles.primary} data-testid="held-physician" onClick={() => resolveHeld("physician")}>
                    Physician (1)
                  </button>
                  <button className={styles.primary} data-testid="held-patient" onClick={() => resolveHeld("patient")}>
                    Patient (2)
                  </button>
                  <button className={styles.secondary} data-testid="held-discard" onClick={() => resolveHeld(null)}>
                    Discard
                  </button>
                </div>
              </div>
            )}
            {/* CDR-008: a companion speaks the patient's language as a labelled third speaker; hands-free never labels one. */}
            <div className={styles.talk}>
              {TALK_SPEAKERS.map((speaker, i) => (
                <button
                  key={speaker}
                  className={`${styles.talkButton} ${styles[speaker]} ${recording === speaker ? styles.recording : ""}`}
                  data-testid={`speak-${speaker}`}
                  onPointerDown={() => void pressTalk(speaker)}
                  onPointerUp={() => void releaseTalk()}
                  onPointerLeave={() => recording === speaker && void releaseTalk()}
                >
                  <span className={styles.eyebrow}>
                    {recording === speaker
                      ? "Listening"
                      : handsFree && speaker !== "companion"
                        ? `Hold ${i + 1} to override`
                        : `Hold or press ${i + 1}`}
                  </span>
                  <span className={styles.talkRole}>{SPEAKER_TEXT[speaker]}</span>
                  <span className={styles.talkLang}>{LANGUAGE_LABELS[languageOf(speaker)].own}</span>
                </button>
              ))}
            </div>
          </section>

          {/* ADR-003 and CDR-001: off the record, a human interpreter, and high-risk moments. */}
          <section className={styles.section} data-testid="safety">
            <h2 className={styles.eyebrow}>Privacy and interpreter</h2>
            {paused && (
              <p className={styles.paused} data-testid="paused" role="status">
                Off the record. Nothing is captured until you resume.
              </p>
            )}
            <div className={styles.actions}>
              <button
                className={paused ? styles.primary : styles.secondary}
                data-testid={paused ? "resume" : "pause"}
                disabled={state !== "open"}
                onClick={() => send(paused ? "visit.resume" : "visit.pause", {})}
              >
                {paused ? "Resume recording" : "Pause, off the record"}
              </button>
              <button
                className={styles.secondary}
                data-testid="interpreter-request"
                disabled={state !== "open" || interpreter?.phase === "connecting"}
                onClick={() => send("interpreter.request", {})}
              >
                Request interpreter
              </button>
              <button
                className={styles.secondary}
                data-testid="mark-high-risk"
                disabled={state !== "open"}
                onClick={() => send("visit.mark_high_risk", {})}
              >
                Mark high risk
              </button>
            </div>
            {interpreter && (
              <div
                className={styles.interpreter}
                data-testid="interpreter"
                data-phase={interpreter.phase}
                aria-live="polite"
              >
                <p className={styles.eyebrow}>
                  Human interpreter
                  {interpreter.phase === "offered" && `: ${REASON_TEXT[interpreter.reason]}`}
                </p>
                <p className={styles.interpreterText}>{INTERPRETER_TEXT[interpreter.phase]}</p>
                {interpreter.phase === "offered" && (
                  <div className={styles.actions}>
                    <button
                      className={styles.primary}
                      data-testid="interpreter-accept"
                      onClick={() => send("interpreter.request", {})}
                    >
                      Connect interpreter
                    </button>
                    <button
                      className={styles.quiet}
                      data-testid="interpreter-dismiss"
                      onClick={() => dismissInterpreter("declined")}
                    >
                      Dismiss
                    </button>
                  </div>
                )}
              </div>
            )}
            {/* CDR-006: every interpreter event is in the record; this list survives a reload. */}
            {escalations.length > 0 && (
              <ol className={styles.recorded} data-testid="escalations" aria-label="Recorded interpreter events">
                {escalations.map((e) => (
                  <li key={e.entryId} data-action={e.action}>
                    <span className={styles.recordedTime}>{clock(e.at)}</span>
                    {ESCALATION_TEXT[e.action]}
                    {e.action === "dismiss" && `: ${DISMISS_TEXT[e.reason as DismissReason] ?? e.reason}`}
                    {e.action === "offer" && `: ${REASON_TEXT[e.reason as EscalationReason] ?? e.reason}`}
                    {e.note && `, ${e.note}`}
                  </li>
                ))}
              </ol>
            )}
          </section>

          <ExplainBackPanel
            state={explainBack}
            results={explainBackResults}
            turns={turns}
            ready={state === "open" && consented && !paused && !pendingReadback}
            send={send}
          />

          {readbackTurn && (
            <section className={styles.readback} data-testid="readback" aria-live="assertive">
              <h2 className={styles.eyebrow}>Read-back: check the values before they are spoken</h2>
              <p className={styles.readbackLine} lang={readbackTurn.sourceLanguage}>
                <Highlighted
                  text={readbackTurn.sourceText}
                  values={readbackTurn.criticalValues.map((v) => v.source)}
                  className={styles.value}
                />
              </p>
              <p className={styles.readbackLine} lang={readbackTurn.targetLanguage}>
                <Highlighted
                  text={readbackTurn.translation}
                  values={readbackTurn.criticalValues.map((v) => v.translated)}
                  className={styles.value}
                />
              </p>
              <ValuesTable turn={readbackTurn} />
              <div className={styles.actions}>
                <button
                  className={styles.primary}
                  data-testid="readback-confirm"
                  onClick={() => decideReadback(readbackTurn.turnId, true)}
                >
                  Confirm and speak
                </button>
                <button
                  className={styles.secondary}
                  data-testid="readback-reject"
                  onClick={() => decideReadback(readbackTurn.turnId, false)}
                >
                  Reject and repeat
                </button>
              </div>
            </section>
          )}

          {nudge && (
            <section className={`${styles.section} ${styles.nudge}`} data-testid="nudge" aria-live="polite">
              <div className={styles.nudgeHead}>
                <h2 className={styles.eyebrow}>Empathy nudge: patient seems {nudge.emotion.replace("_", " ")}</h2>
                <button className={styles.quiet} onClick={() => setDismissed((d) => new Set(d).add(nudge.turnId))}>
                  Dismiss
                </button>
              </div>
              <p className={styles.suggestion}>{nudge.suggestion}</p>
              <blockquote lang={nudge.phraseLanguage}>{nudge.phrase}</blockquote>
            </section>
          )}

          <section className={styles.section}>
            <h2 className={styles.eyebrow}>Typed turn</h2>
            <div className={styles.typed}>
              <select
                data-testid="typed-speaker"
                value={typedSpeaker}
                onChange={(e) => setTypedSpeaker(e.target.value as Speaker)}
              >
                <option value="physician">Physician (English)</option>
                <option value="patient">Patient ({LANGUAGE_LABELS[patientLanguage].english})</option>
                <option value="companion">Companion ({LANGUAGE_LABELS[patientLanguage].english})</option>
              </select>
              <textarea
                data-testid="typed-text"
                value={typedText}
                onChange={(e) => setTypedText(e.target.value)}
                rows={2}
                placeholder="Type what was said"
              />
              <button
                className={styles.primary}
                data-testid="typed-send"
                onClick={sendTyped}
                disabled={state !== "open" || paused || !consented}
              >
                Send
              </button>
            </div>
            {notice && (
              <p className={styles.notice} role="status" data-testid="notice">
                {notice}
              </p>
            )}
          </section>

          <NoteSummaryPanel
            open={state === "open"}
            note={note}
            noteStale={noteStale}
            noteStatus={noteStatus}
            summary={summary}
            summaryStale={summaryStale}
            summaryStatus={summaryStatus}
            summaryChecks={summaryChecks}
            turns={turns}
            send={send}
          />

          {/* TDM-002: folded away so it is never pressed by accident; its state shows on the fold itself. */}
          <details className={styles.presenter} data-testid="presenter">
            <summary>
              <span className={styles.eyebrow}>Presenter</span>
              {injection === "armed" && (
                <span className={`${styles.tag} ${styles.stop}`} data-testid="injection-state">
                  mismatch armed
                </span>
              )}
              {tamper && (
                <span className={`${styles.tag} ${styles.stop}`} data-testid="tamper-fold-state">
                  record altered
                </span>
              )}
            </summary>
            <div className={styles.presenterBody}>
              <p className={styles.aside}>
                Mismatch control for the blocked-dose beat. Never shown on the shared screen or the review screen.
              </p>
              {injection && (
                <p className={styles.injection} data-testid="injection" data-state={injection}>
                  {INJECTION_TEXT[injection]}
                </p>
              )}
              <div className={styles.actions}>
                {injection === "armed" ? (
                  <button
                    className={styles.secondary}
                    data-testid="injection-cancel"
                    onClick={() => send("demo.cancel_injection", {})}
                  >
                    Cancel mismatch
                  </button>
                ) : (
                  <button
                    className={styles.secondary}
                    data-testid="injection-arm"
                    disabled={state !== "open"}
                    onClick={() => send("demo.inject_mismatch", {})}
                  >
                    Arm mismatch
                  </button>
                )}
              </div>
              {/* TDM-005: once per visit; the badge turns from the server's own verification, never from here. */}
              <div className={styles.tamper} data-testid="tamper" data-state={tamper ? "fired" : "ready"}>
                <p className={styles.aside}>
                  Tamper control for the record beat: alters one stored turn without rehashing it, once per visit. The
                  TV shows only the broken badge.
                </p>
                {tamper ? (
                  <p className={styles.injection} data-state="fired" data-testid="tamper-state">
                    Altered {brokenEntryLabel(tamper.entryId, turns.map((t) => t.turnId), segments) ?? "an entry"} at{" "}
                    {clock(tamper.at)}. Start a new visit to use it again.
                  </p>
                ) : (
                  <div className={styles.tamperRow}>
                    <select
                      data-testid="tamper-target"
                      aria-label="Entry to alter"
                      value={target}
                      disabled={!tamperTargets.length}
                      onChange={(e) => setTamperTarget(e.target.value)}
                    >
                      {tamperTargets.length === 0 && <option value="">No settled turn yet</option>}
                      {tamperTargets.map((t) => (
                        <option key={t.entryId} value={t.entryId}>
                          {t.label.length > 72 ? `${t.label.slice(0, 71)}…` : t.label}
                        </option>
                      ))}
                    </select>
                    <button
                      className={styles.secondary}
                      data-testid="tamper-fire"
                      disabled={state !== "open" || !target}
                      onClick={() => send("demo.tamper_record", { entryId: target })}
                    >
                      Alter record
                    </button>
                  </div>
                )}
              </div>
            </div>
          </details>
        </div>

        <aside className={styles.panel} aria-label="Turn log and latency">
          <section className={`${styles.section} ${styles.latency}`}>
            <div>
              <h2 className={styles.eyebrow}>Median end of speech to audio</h2>
              <p className={styles.stat}>{medianMs === undefined ? "n/a" : `${(medianMs / 1000).toFixed(2)} s`}</p>
              <p className={styles.aside}>
                Over {measured.length} turn{measured.length === 1 ? "" : "s"}. Target under 3 s. Read-back decisions are
                not counted.
              </p>
              <dl className={styles.breakdown} data-testid="latency-breakdown">
                {breakdown.map(({ label, ms }) => (
                  <div key={label}>
                    <dt className={styles.eyebrow}>{label}</dt>
                    <dd>{ms === undefined ? "n/a" : `${(ms / 1000).toFixed(2)} s`}</dd>
                  </div>
                ))}
              </dl>
            </div>
            <button className={styles.secondary} onClick={downloadCsv} disabled={!latency.length}>
              Download CSV
            </button>
          </section>

          {/* CDR-008 and MDD-005 rule 4: how the visit is landing, for the physician only; a quiet list, newest last. */}
          <section className={styles.section} data-testid="trust" aria-label="Trust, private to the physician">
            <h2 className={styles.eyebrow}>Trust, private to the physician</h2>
            {trust.length === 0 && <p className={styles.aside}>How the visit is landing shows here, turn by turn.</p>}
            <ol className={styles.trust}>
              {trust.map((u, i) => {
                const after = u.turnId ? turns.findIndex((t) => t.turnId === u.turnId) + 1 : 0;
                if (u.signal) {
                  return (
                    <li key={`${u.at}-${i}`} data-testid="trust-signal" data-signal={u.signal} data-after-turn={u.turnId ?? undefined}>
                      <p className={styles.trustLine}>
                        <span className={`${styles.trustSpeaker} ${styles.patient}`}>{SIGNAL_TEXT[u.signal]}</span>
                        {after > 0 && <span className={styles.trustAfter}>after turn {after}</span>}
                      </p>
                      {u.cue && (
                        <p className={styles.cue} data-testid="cue" data-kind={u.cue.kind}>
                          {u.cue.text}
                        </p>
                      )}
                    </li>
                  );
                }
                const speaker = u.speaker ?? "patient";
                const reading =
                  speaker === "physician"
                    ? MANNER_TEXT[u.manner ?? "plain"]
                    : u.emotion
                      ? EMOTION_TEXT[u.emotion]
                      : null;
                return (
                  <li
                    key={`${u.at}-${i}`}
                    data-testid="trust-turn"
                    data-speaker={speaker}
                    data-emotion={u.emotion ?? undefined}
                    data-manner={u.manner ?? undefined}
                  >
                    <p className={styles.trustLine}>
                      <span className={`${styles.trustSpeaker} ${styles[speaker]}`}>{SPEAKER_TEXT[speaker]}</span>
                      {reading && <span>{reading}</span>}
                      {after > 0 && <span className={styles.trustAfter}>turn {after}</span>}
                    </p>
                    {u.reassuranceLanded !== null && (
                      <p
                        className={u.reassuranceLanded ? styles.landed : styles.notLanded}
                        data-testid="landed"
                        data-landed={u.reassuranceLanded ? "true" : "false"}
                      >
                        {u.reassuranceLanded ? "Reassurance landed" : "Still worried after reassurance"}
                      </p>
                    )}
                    {u.cue && (
                      <p className={styles.cue} data-testid="cue" data-kind={u.cue.kind}>
                        {/* The Empathy nudge panel already shows the suggestion with its phrase; this only points to it. */}
                        {u.cue.kind === "reassurance" ? "Empathy nudge shown" : u.cue.text}
                      </p>
                    )}
                  </li>
                );
              })}
            </ol>
          </section>

          <section className={styles.section}>
            <h2 className={styles.eyebrow}>Turns, private to the physician</h2>
            {turns.length === 0 && markers.length === 0 && <p className={styles.aside}>Nothing said yet.</p>}
            <ol className={styles.turns}>
              {markersAfter(null)}
              {turns.flatMap((t) => {
                const outcome = outcomes[t.turnId] ?? {};
                const unspoken =
                  t.status === "blocked" || t.status === "escalated" || outcome.discarded || outcome.voiceFailed;
                const wasInjected = injected.has(t.turnId);
                const altered = t.turnId === brokenTurnId;
                const tampered = t.turnId === tamperedTurnId;
                const history = segments.find((h) => h.segmentId === t.turnId);
                const now = effective(t, history);
                return [
                  <li
                    key={t.turnId}
                    data-testid="turn"
                    data-status={t.status}
                    data-injected={wasInjected || undefined}
                    data-broken={altered || undefined}
                    data-tampered={tampered || undefined}
                  >
                    <div className={styles.turnHead}>
                      <span className={`${styles.speaker} ${styles[t.speaker]}`}>{SPEAKER_TEXT[t.speaker]}</span>
                      <span className={`${styles.tag} ${unspoken ? styles.stop : ""}`}>
                        {statusText(t, outcome, t.turnId === pendingReadback)}
                      </span>
                      {/* IDR-005: how the speaker said it, read from the words; the patient's stays private here. Plain goes unsaid. */}
                      {t.manner && t.manner !== "plain" && (
                        <span className={styles.manner} data-testid="turn-manner" data-manner={t.manner}>
                          {MANNER_TEXT[t.manner]}
                        </span>
                      )}
                      {wasInjected && (
                        <span className={`${styles.tag} ${styles.stop}`} data-testid="injected">
                          presenter mismatch
                        </span>
                      )}
                      {altered && (
                        <span className={`${styles.tag} ${styles.stop}`} data-testid="record-broken-here">
                          record broken here
                        </span>
                      )}
                      {tampered && (
                        <span className={`${styles.tag} ${styles.stop}`} data-testid="tampered">
                          altered by the tamper control
                        </span>
                      )}
                      {now.corrected && (
                        <span className={styles.tag} data-testid="corrected">
                          corrected by the patient
                        </span>
                      )}
                      {isConfirmed(history) && (
                        <span className={styles.tag} data-testid="confirmed">
                          confirmed by the patient
                        </span>
                      )}
                    </div>
                    <p className={styles.line} lang={t.sourceLanguage}>
                      {now.sourceText}
                    </p>
                    <p className={`${styles.line} ${unspoken ? styles.unspoken : ""}`} lang={t.targetLanguage}>
                      {now.translation}
                    </p>
                    {now.corrected && (
                      <p className={styles.analysis}>
                        Original: <span lang={t.sourceLanguage}>{t.sourceText}</span>
                      </p>
                    )}
                    {t.status === "blocked" && (
                      <>
                        <ValuesTable turn={t} only="mismatched" />
                        <p className={styles.instruction}>Ask the speaker to repeat or rephrase.</p>
                        {wasInjected && (
                          <p className={styles.analysis}>
                            The presenter injected this mismatch (TDM-002): the dose was multiplied by 10 after
                            translation, on both attempts.
                          </p>
                        )}
                      </>
                    )}
                    {t.status === "escalated" && (
                      <p className={styles.instruction}>
                        {outcome.escalation ? `Not spoken: ${REASON_TEXT[outcome.escalation]}. ` : "Not spoken. "}
                        Offer a human interpreter.
                      </p>
                    )}
                    <p className={styles.analysis}>
                      Back: {t.backTranslation}. {t.emotion.replace("_", " ")}, certainty {t.certainty}, confidence{" "}
                      {t.confidence.toFixed(2)}, attempts {t.attempts}.
                    </p>
                  </li>,
                  ...markersAfter(t.turnId),
                ];
              })}
            </ol>
          </section>
        </aside>
      </div>
    </main>
  );
}
