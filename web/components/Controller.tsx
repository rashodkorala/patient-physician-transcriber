"use client";

/**
 * Physician controller: languages, names, push-to-talk, hands-free listening, typed fallback, read-back, nudges,
 * turns, and latency.
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
 * @contract ws:/ws/visit
 */

import { useCallback, useEffect, useEffectEvent, useRef, useState } from "react";
import type {
  DemoInjectionState,
  EmpathyNudge,
  Envelope,
  ErrorPayload,
  EscalationReason,
  InterpreterEscalation,
  InterpreterLine,
  IntroductionState,
  Language,
  NameProposed,
  NameRole,
  Names,
  PatientLanguage,
  Speaker,
  ToneLabel,
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
import { type LatencyRow, median, segments, toCsv } from "@/lib/latency";
import { serverHttpUrl, useVisitSocket } from "@/lib/socket";
import { playbackMessages } from "@/lib/speaking";
import {
  type Capture,
  type Heard,
  type Listening,
  current,
  onSpeaking,
  speak,
  startCapture,
  startListening,
  warmUp,
} from "@/lib/speech";
import styles from "./controller.module.css";
import Highlighted from "./Highlighted";

const TONE_LABELS: ToneLabel[] = ["respectful", "reassuring", "empathetic", "neutral"];

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

function toneLabel(turn: TurnResult): ToneLabel {
  return (turn.toneTags.find((t) => (TONE_LABELS as string[]).includes(t)) as ToneLabel | undefined) ?? "neutral";
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

  const physicianLanguage: Language = "en-CA";
  const languageOf = (speaker: Speaker): Language => (speaker === "physician" ? physicianLanguage : patientLanguage);

  const updateLatency = (turnId: string, patch: Partial<LatencyRow>) =>
    setLatency((rows) => rows.map((r) => (r.turnId === turnId ? { ...r, ...patch } : r)));
  const updateOutcome = (turnId: string, patch: Outcome) =>
    setOutcomes((all) => ({ ...all, [turnId]: { ...all[turnId], ...patch } }));

  const startCall = () => {
    callTimers.current.forEach(clearTimeout);
    setInterpreter({ phase: "connecting", reason: "requested" });
    callTimers.current = [
      setTimeout(() => setInterpreter({ phase: "simulated", reason: "requested" }), INTERPRETER_CONNECTING_MS),
      setTimeout(() => setInterpreter(null), INTERPRETER_CONNECTING_MS + INTERPRETER_SIMULATED_MS),
    ];
  };

  useEffect(() => () => callTimers.current.forEach(clearTimeout), []);

  const receiveNames = (current: Names) => {
    const last = serverNames.current;
    if (current.physicianName !== last.physicianName) setPhysicianDraft(current.physicianName ?? "");
    if (current.patientName !== last.patientName) setPatientDraft(current.patientName ?? "");
    serverNames.current = current;
    setNames(current);
  };

  const onEvent = useCallback((event: Envelope) => {
    switch (event.type) {
      case "visit.state": {
        const state = event.payload as VisitStateController;
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
        // speak() keeps lines in order and fetches each one's audio straight away.
        for (const { language, text } of line.lines) {
          speak(text, language, line.lineId).catch((error: Error) => setNotice(`Not spoken: ${error.message}`));
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
        const now = Date.now();
        const times = pendingTimes.current.shift() ?? { endOfSpeechAt: now, submittedAt: now };
        setLatency((rows) => [...rows, { turnId: started.turnId, speaker: started.speaker, ...times }]);
        break;
      }
      case "turn.status": {
        const status = event.payload as TurnStatus;
        if (status.stage === "discarded") {
          updateOutcome(status.turnId, { discarded: true });
          setPendingReadback((p) => (p === status.turnId ? null : p));
          setNotice("Dose rejected and not spoken. Ask the physician to say it again.");
        }
        break;
      }
      case "turn.analysis": {
        const result = event.payload as TurnResult;
        updateLatency(result.turnId, { analysisAt: Date.now() });
        setTurns((prev) => [...prev.filter((t) => t.turnId !== result.turnId), result]);
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
        updateLatency(caption.turnId, { resultAt: Date.now(), spoken: caption.status === "final" });
        // The public caption is the signal to speak (CDR-002: shown only once spoken).
        if (caption.status === "final" && caption.translation) {
          updateOutcome(caption.turnId, { spoken: true });
          setPendingReadback((p) => (p === caption.turnId ? null : p));
          speak(caption.translation, caption.targetLanguage, caption.turnId)
            .then(({ startedAt }) => updateLatency(caption.turnId, { speechStartAt: startedAt }))
            .catch((error: Error) => {
              updateOutcome(caption.turnId, { voiceFailed: true });
              setNotice(`Not spoken: ${error.message}`);
            });
        }
        break;
      }
      case "interpreter.escalation": {
        const { reason, turnId } = event.payload as InterpreterEscalation;
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
        else setNotice(error.message);
        break;
      }
    }
  }, []);

  const { state, send } = useVisitSocket("controller", onEvent);

  useEffect(() => {
    fetch(`${serverHttpUrl()}/api/health`)
      .then((response) => response.json())
      .then((health: { testLanguages?: boolean }) => setTestMode(Boolean(health.testLanguages)))
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

  // Hold 1 for the physician and 2 for the patient; with a short reply waiting, 1 or 2 says whose it was.
  useEffect(() => {
    const keyToSpeaker: Record<string, Speaker> = { "1": "physician", "2": "patient" };
    const down = (e: KeyboardEvent) => {
      const speaker = keyToSpeaker[e.key];
      const focused = document.activeElement;
      const typing =
        focused instanceof HTMLTextAreaElement || (focused instanceof HTMLInputElement && focused.type === "text");
      if (!speaker || e.repeat || typing) return;
      if (held.length) resolveHeld(speaker);
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

  const measured = latency.map(segments).filter((s) => s.totalMs !== undefined);
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
            {m.reason === "high_risk" ? "Marked high risk · interpreter offered" : "Human interpreter requested"}
          </span>
        </li>
      ));

  const readbackTurn = turns.find((t) => t.turnId === pendingReadback);
  const nudge = [...nudges].reverse().find((n) => !dismissed.has(n.turnId));

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Demo night interpreter</p>
          <h1>Physician controller</h1>
        </div>
        <span className={`${styles.status} ${styles[state]}`} data-testid="connection">
          {state}
        </span>
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
                  disabled={turns.length > 0}
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
                        {own} ({english}){note && ` · ${note}`}
                      </option>
                    );
                  })}
                </select>
              </label>
              <p className={styles.aside}>With English. Fixed once the first turn starts.</p>
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
            <div className={styles.intro} data-testid="introduction" data-state={introSkipped ? "skipped" : introduction}>
              {introduction === "pending" && turns.length === 0 && (
                <>
                  <button
                    className={styles.secondary}
                    data-testid="intro-start"
                    disabled={state !== "open"}
                    onClick={() => send("visit.start_introduction", {})}
                  >
                    Start introduction
                  </button>
                  <p className={styles.aside}>The interpreter greets you both and asks for any name it does not know.</p>
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
          </section>

          <section className={styles.section}>
            <div className={styles.speakHead}>
              <h2 className={styles.eyebrow}>Speak</h2>
              <label className={styles.check}>
                <input
                  type="checkbox"
                  data-testid="hands-free"
                  checked={handsFree}
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
                    {" "}
                    · last heard {lastHeard.speaker}, {LANGUAGE_LABELS[lastHeard.language].own}
                  </span>
                )}
              </p>
            )}
            {held[0] && (
              <div className={styles.held} data-testid="held-reply" aria-live="assertive">
                <p className={styles.eyebrow}>Short reply · whose words were these?</p>
                <p className={styles.heldText} data-testid="held-text">
                  {held[0].text}
                </p>
                <div className={styles.actions}>
                  <button className={styles.primary} data-testid="held-physician" onClick={() => resolveHeld("physician")}>
                    Physician · 1
                  </button>
                  <button className={styles.primary} data-testid="held-patient" onClick={() => resolveHeld("patient")}>
                    Patient · 2
                  </button>
                  <button className={styles.secondary} data-testid="held-discard" onClick={() => resolveHeld(null)}>
                    Discard
                  </button>
                </div>
              </div>
            )}
            <div className={styles.talk}>
              {(["physician", "patient"] as Speaker[]).map((speaker, i) => (
                <button
                  key={speaker}
                  className={`${styles.talkButton} ${recording === speaker ? styles.recording : ""}`}
                  onPointerDown={() => void pressTalk(speaker)}
                  onPointerUp={() => void releaseTalk()}
                  onPointerLeave={() => recording === speaker && void releaseTalk()}
                >
                  <span className={styles.eyebrow}>
                    {recording === speaker ? "Listening" : handsFree ? `Hold ${i + 1} to override` : `Hold or press ${i + 1}`}
                  </span>
                  <span className={styles.talkRole}>{speaker === "physician" ? "Physician" : "Patient"}</span>
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
                  {interpreter.phase === "offered" && ` · ${REASON_TEXT[interpreter.reason]}`}
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
                    <button className={styles.quiet} onClick={() => setInterpreter(null)}>
                      Dismiss
                    </button>
                  </div>
                )}
              </div>
            )}
          </section>

          {readbackTurn && (
            <section className={styles.readback} data-testid="readback" aria-live="assertive">
              <h2 className={styles.eyebrow}>Read-back · check the values before they are spoken</h2>
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
                <h2 className={styles.eyebrow}>Empathy nudge · patient seems {nudge.emotion.replace("_", " ")}</h2>
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
                disabled={state !== "open" || paused}
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

          {/* TDM-002: folded away so it is never pressed by accident; its state shows on the fold itself. */}
          <details className={styles.presenter} data-testid="presenter">
            <summary>
              <span className={styles.eyebrow}>Presenter</span>
              {injection === "armed" && (
                <span className={`${styles.tag} ${styles.stop}`} data-testid="injection-state">
                  mismatch armed
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

          <section className={styles.section}>
            <h2 className={styles.eyebrow}>Turns · private to the physician</h2>
            {turns.length === 0 && markers.length === 0 && <p className={styles.aside}>Nothing said yet.</p>}
            <ol className={styles.turns}>
              {markersAfter(null)}
              {turns.flatMap((t) => {
                const outcome = outcomes[t.turnId] ?? {};
                const unspoken =
                  t.status === "blocked" || t.status === "escalated" || outcome.discarded || outcome.voiceFailed;
                const wasInjected = injected.has(t.turnId);
                return [
                  <li key={t.turnId} data-testid="turn" data-status={t.status} data-injected={wasInjected || undefined}>
                    <div className={styles.turnHead}>
                      <span className={`${styles.speaker} ${styles[t.speaker]}`}>{t.speaker}</span>
                      <span className={`${styles.tag} ${unspoken ? styles.stop : ""}`}>
                        {statusText(t, outcome, t.turnId === pendingReadback)}
                      </span>
                      {!unspoken && <span className={styles.tag}>{toneLabel(t)}</span>}
                      {wasInjected && (
                        <span className={`${styles.tag} ${styles.stop}`} data-testid="injected">
                          presenter mismatch
                        </span>
                      )}
                    </div>
                    <p className={styles.line} lang={t.sourceLanguage}>
                      {t.sourceText}
                    </p>
                    <p className={`${styles.line} ${unspoken ? styles.unspoken : ""}`} lang={t.targetLanguage}>
                      {t.translation}
                    </p>
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
                      Back: {t.backTranslation} · {t.emotion.replace("_", " ")} · certainty {t.certainty} · confidence{" "}
                      {t.confidence.toFixed(2)} · attempts {t.attempts}
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
