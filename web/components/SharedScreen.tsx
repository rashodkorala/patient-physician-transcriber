"use client";

/**
 * Shared TV screen: large side-by-side captions. Receives only public events.
 *
 * @implements CDR-001: Visit WebSocket event contract
 * @implements CDR-002: Turn result schema
 * @implements CDR-003: Participant names and interpreter lines on the visit channel
 * @implements CDR-004: Interpreter voice playback on the visit channel
 * @implements ADR-003: Human interpreter escalation on low confidence and high-risk moments
 * @implements CDR-005: Consent and explain-back on the visit channel
 * @implements CDR-006: Record chain entries, review corrections, interpreter dismissal, and presenter controls
 * @implements IDR-003: SHA-256 hash chain for the record-verified badge
 * @implements CDR-007: Clinical note with provenance and patient summary on the visit channel
 * @implements CDR-008: Patient signals, manner, trust updates, companion turns, and the closing check on the visit channel
 * @implements IDR-005: Manner vocabulary and voice delivery
 * @implements ADR-012: Clinic design system
 * @contract TurnCaption
 */

import { type ReactNode, useCallback, useEffect, useRef, useState } from "react";
import type {
  ArtefactsStale,
  ArtefactStatus,
  ConsentNotice,
  ExplainBackState,
  PatientSummary,
  SegmentAmended,
  SegmentHistory,
  ConsentState,
  Envelope,
  InterpreterEscalation,
  InterpreterLine,
  Language,
  LinePurpose,
  Names,
  PatientSignalEntry,
  RecordIntegrity,
  Speaker,
  TurnCaption,
  TurnStarted,
  TurnStatus,
  VisitStatePublic,
  VoiceSpeaking,
} from "@/lib/contracts";
import {
  INTERPRETER_CONNECTING_MS,
  INTERPRETER_SIMULATED_MS,
  type InterpreterPhase,
  type NoticeKey,
  SIGNAL_KEY,
  bilingual,
  heldBackNotice,
  mannerLabel,
} from "@/lib/i18n";
import { LANGUAGE_LABELS } from "@/lib/languages";
import { applyAmended, brokenEntryLabel, summaryIndexOf, turnOfEntry, visitChanged } from "@/lib/record";
import { type ConnectionState, useVisitSocket } from "@/lib/socket";
import { signalShownFor } from "@/lib/trust";
import Highlighted from "./Highlighted";
import Orb, { type OrbMode } from "./Orb";
import RecordBadge from "./RecordBadge";
import styles from "./screen.module.css";

interface Pending {
  turnId: string;
  speaker: Speaker;
  stage: string;
  language?: Language;
  // Known only from a visit.state snapshot; live events carry no text before a turn settles.
  sourceText?: string;
}

const SPEAKER_LABEL: Record<Speaker, string> = { physician: "Physician", patient: "Patient", companion: "Companion" };
const STATE_LABEL: Record<ConnectionState, string> = { open: "Connected", connecting: "Connecting", closed: "Reconnecting" };
/**
 * CDR-008: interpreter lines said during the visit; they stay until the next turn settles, unlike the introduction.
 * ADR-003: the say-it-again request after an unclear turn is one of them.
 */
const MID_VISIT_LINES = new Set<LinePurpose>(["signal_not_understood", "signal_slower", "ask_if_clear", "ask_to_repeat"]);

function Notice({ notice, first, second }: { notice: NoticeKey; first: Language; second: Language }) {
  return (
    <div className={styles.notice} data-testid={`notice-${notice}`}>
      {bilingual(notice, first, second).map(({ lang, text }) => (
        <p key={lang} lang={lang}>
          {text}
        </p>
      ))}
    </div>
  );
}

/** The original, with the speaker label, and their name when known, above it. */
function Original({
  speaker,
  name,
  language,
  caption = false,
  tag,
  children,
}: {
  speaker: Speaker;
  name?: string | null;
  language?: Language;
  caption?: boolean;
  tag?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className={styles.side} lang={language}>
      <div className={styles.meta}>
        <span className={styles.speaker}>{SPEAKER_LABEL[speaker]}</span>
        {name && (
          <span className={styles.name} data-testid="speaker-name">
            {name}
          </span>
        )}
        {caption && <span className={styles.columnLabel} lang="en-CA">Original</span>}
        {language && <span className={styles.lang}>{LANGUAGE_LABELS[language].own}</span>}
        {tag}
      </div>
      {children}
    </div>
  );
}

function NotSpoken() {
  return <span className={`${styles.tag} ${styles.stop}`}>Not spoken</span>;
}

/** The interpreter speaking for itself: the introduction and its questions, in each language spoken. */
function Line({ line }: { line: InterpreterLine }) {
  return (
    <article
      className={`${styles.turn} ${styles.interpreter}`}
      data-testid="interpreter-line"
      data-purpose={line.purpose}
    >
      {line.lines.map(({ language, text }) => (
        <div key={language} className={styles.side} lang={language}>
          <div className={styles.meta}>
            <span className={styles.speaker}>Interpreter</span>
            <span className={styles.lang}>{LANGUAGE_LABELS[language].own}</span>
          </div>
          <p className={styles.text}>{text}</p>
        </div>
      ))}
    </article>
  );
}

/** The resting orb over a quiet line in both languages: before the first turn, and while off the record. */
function Resting({
  notice,
  testId,
  languages,
}: {
  notice: NoticeKey;
  testId: string;
  languages: { patient: Language; physician: Language };
}) {
  return (
    <div className={styles.ready} data-testid={testId} aria-live="polite">
      <Orb mode="ready" className={styles.readyOrb} />
      {bilingual(notice, languages.patient, languages.physician).map(({ lang, text }) => (
        <p key={lang} lang={lang}>
          {text}
        </p>
      ))}
    </div>
  );
}

const PHASE_NOTICE: Record<InterpreterPhase, NoticeKey> = {
  offered: "interpreterAvailable",
  connecting: "interpreterConnecting",
  simulated: "interpreterSimulated",
};

/** ADR-003: a human interpreter offered, connecting, or (simulated) joining, as an Interpreter row in both languages. */
function InterpreterNotice({
  phase,
  patient,
  physician,
}: {
  phase: InterpreterPhase;
  patient: Language;
  physician: Language;
}) {
  return (
    <article
      className={`${styles.turn} ${styles.interpreter} ${styles.escalation}`}
      data-testid="interpreter-notice"
      data-phase={phase}
      aria-live="polite"
    >
      {bilingual(PHASE_NOTICE[phase], patient, physician).map(({ lang, text }) => (
        <div key={lang} className={styles.side} lang={lang}>
          <div className={styles.meta}>
            <span className={styles.speaker}>Interpreter</span>
            <span className={styles.lang}>{LANGUAGE_LABELS[lang].own}</span>
            {phase === "connecting" && <span className={styles.tag}>Connecting</span>}
            {phase === "simulated" && <span className={styles.tag}>Simulated</span>}
          </div>
          <p className={styles.text}>{text}</p>
        </div>
      ))}
    </article>
  );
}

/**
 * CDR-005: the consent notice, as the interpreter's own words in the patient's language and in English, shown
 * until consent is given and again once it is withdrawn. The text comes from the server, so every screen shows
 * exactly the notice that was agreed to.
 */
function ConsentNoticeRow({ notice }: { notice: ConsentNotice }) {
  return (
    <article
      className={`${styles.turn} ${styles.interpreter} ${styles.consent}`}
      data-testid="consent-notice"
      data-notice-id={notice.noticeId}
      aria-live="polite"
    >
      {notice.lines.map(({ language, text }) => (
        <div key={language} className={styles.side} lang={language}>
          <div className={styles.meta}>
            <span className={styles.speaker}>Consent</span>
            <span className={styles.lang}>{LANGUAGE_LABELS[language].own}</span>
          </div>
          <p className={styles.text}>{text}</p>
        </div>
      ))}
    </article>
  );
}

/** CDR-005: a prompt for the patient while an explain-back listens, in both languages; never an outcome. */
function ExplainBackPrompt({
  state,
  patient,
  physician,
}: {
  state: ExplainBackState["state"];
  patient: Language;
  physician: Language;
}) {
  const key: NoticeKey = state === "listening" ? "explainBackListening" : "explainBackChecking";
  return (
    <article
      className={`${styles.turn} ${styles.interpreter} ${styles.escalation}`}
      data-testid="explainback-prompt"
      data-state={state}
    >
      {bilingual(key, patient, physician).map(({ lang, text }) => (
        <div key={lang} className={styles.side} lang={lang}>
          <div className={styles.meta}>
            <span className={styles.speaker}>Interpreter</span>
            <span className={styles.lang}>{LANGUAGE_LABELS[lang].own}</span>
          </div>
          <p className={styles.text}>{text}</p>
        </div>
      ))}
    </article>
  );
}

/**
 * CDR-007: the patient's summary, only once it passed its value check, in the patient's language; the sentence
 * being read aloud is inked in. Before that, a quiet line that it is being prepared, or that it is not ready.
 */
function SummaryRow({
  summary,
  stage,
  stale,
  playing,
  patient,
  physician,
}: {
  summary: PatientSummary | null;
  stage: ArtefactStatus["stage"] | null;
  stale: boolean;
  playing: number | null;
  patient: Language;
  physician: Language;
}) {
  if (!summary) {
    const key: NoticeKey = stage === "refused" ? "summaryRefused" : "summaryPreparing";
    return (
      <article className={`${styles.turn} ${styles.interpreter}`} data-testid="summary" data-state={stage ?? undefined}>
        {bilingual(key, patient, physician).map(({ lang, text }) => (
          <div key={lang} className={styles.side} lang={lang}>
            <div className={styles.meta}>
              <span className={styles.speaker}>Summary</span>
              <span className={styles.lang}>{LANGUAGE_LABELS[lang].own}</span>
            </div>
            <p className={styles.text}>{text}</p>
          </div>
        ))}
      </article>
    );
  }
  return (
    <article className={`${styles.turn} ${styles.interpreter} ${styles.summary}`} data-testid="summary" data-state="ready">
      <div className={styles.side} lang={summary.language}>
        <div className={styles.meta}>
          <span className={styles.speaker}>Summary</span>
          <span className={styles.lang}>{LANGUAGE_LABELS[summary.language].own}</span>
          {stale && (
            <span className={styles.tag} data-testid="summary-stale">
              Record changed since
            </span>
          )}
        </div>
        <ol className={styles.sentences}>
          {[...summary.sentences]
            .sort((a, b) => a.index - b.index)
            .map((s) => (
              <li
                key={s.sentenceId}
                className={playing === s.index ? styles.playing : undefined}
                data-playing={playing === s.index || undefined}
              >
                <span>
                  <Highlighted text={s.text} values={summary.values.map((v) => v.text)} className={styles.value} />
                </span>
              </li>
            ))}
        </ol>
      </div>
    </article>
  );
}

/**
 * CDR-008: the patient's own signal, as a notice to the room in the patient's language and in English, in the
 * patient's colour and under their name. Shown for a few seconds only; the interpreter's line to the physician follows.
 */
function SignalRow({
  entry,
  name,
  patient,
  physician,
}: {
  entry: PatientSignalEntry;
  name: string | null;
  patient: Language;
  physician: Language;
}) {
  return (
    <article
      className={`${styles.turn} ${styles.patient} ${styles.signal}`}
      data-testid="patient-signal"
      data-signal={entry.signal}
      data-signal-id={entry.signalId}
      aria-live="polite"
    >
      {bilingual(SIGNAL_KEY[entry.signal].notice, patient, physician).map(({ lang, text }) => (
        <div key={lang} className={styles.side} lang={lang}>
          <div className={styles.meta}>
            <span className={styles.speaker} lang="en-CA">Patient request</span>
            {name && <span className={styles.name}>{name}</span>}
            <span className={styles.lang}>{LANGUAGE_LABELS[lang].own}</span>
          </div>
          <p className={styles.text}>{text}</p>
        </div>
      ))}
    </article>
  );
}

/**
 * IDR-005: how the physician said it, beneath the translation: the patient's language first, English beside it
 * for the physician. Plain renders nothing, and a patient or companion caption never carries a manner.
 */
function MannerLabel({ c, patient }: { c: TurnCaption; patient: Language }) {
  if (c.speaker !== "physician" || c.status !== "final") return null;
  const own = mannerLabel(c.manner, patient);
  if (!own) return null;
  return (
    <p className={styles.manner} data-testid="manner-label" data-manner={c.manner}>
      <span lang={patient}>{own}</span>
      <span lang="en-CA">{mannerLabel(c.manner, "en-CA")}</span>
    </p>
  );
}

function nameOf(speaker: Speaker, names: Names): string | null {
  if (speaker === "physician") return names.physicianName ?? null;
  if (speaker === "patient") return names.patientName ?? null;
  return null;
}

function Caption({ c, names, broken, patient }: { c: TurnCaption; names: Names; broken: boolean; patient: Language }) {
  const spoken = c.status === "final" && c.translation !== null;
  return (
    <article
      className={`${styles.turn} ${styles[c.speaker]} ${broken ? styles.broken : ""}`}
      data-testid="caption"
      data-turn-id={c.turnId}
      data-status={c.status}
      data-speaker={c.speaker}
      data-broken={broken || undefined}
    >
      <Original
        speaker={c.speaker}
        name={nameOf(c.speaker, names)}
        language={c.sourceLanguage}
        caption
        tag={
          // CDR-006: the turn record.integrity names, and never a word about how it was altered.
          broken && (
            <span className={`${styles.tag} ${styles.stop}`} data-testid="record-broken-here">
              Record broken here
            </span>
          )
        }
      >
        <p className={styles.text}>
          <Highlighted text={c.sourceText} values={c.criticalValues.map((v) => v.source)} className={styles.value} />
        </p>
      </Original>
      <div className={spoken ? styles.side : `${styles.side} ${styles.heldBack}`} lang={spoken ? c.targetLanguage : undefined}>
        <div className={styles.meta}>
          <span className={styles.columnLabel} lang="en-CA">Translation</span>
          <span className={styles.lang}>{LANGUAGE_LABELS[c.targetLanguage].own}</span>
          {!spoken && <NotSpoken />}
        </div>
        {spoken ? (
          <>
            <p className={styles.text}>
              <Highlighted
                text={c.translation ?? ""}
                values={c.criticalValues.map((v) => v.translated)}
                className={styles.value}
              />
            </p>
            <MannerLabel c={c} patient={patient} />
            {c.glossaryUsed.length > 0 && (
              <dl className={styles.glossary} data-testid="glossary">
                {c.glossaryUsed.map((g) => (
                  <div key={g.term}>
                    <dt>{g.translation}</dt>
                    <dd>{g.explanation}</dd>
                  </div>
                ))}
              </dl>
            )}
          </>
        ) : (
          <Notice notice={heldBackNotice(c.status)} first={c.targetLanguage} second={c.sourceLanguage} />
        )}
      </div>
    </article>
  );
}

/** Listening in the speaker's colour; every later stage until the result is translating; a dropped turn rests. */
function orbMode(p: Pending): OrbMode {
  if (p.stage === "listening") return p.speaker === "physician" ? "physician" : "patient";
  if (p.stage === "discarded" || p.stage === "failed") return "ready";
  return "translating";
}

const ORB_LABEL: Record<OrbMode, string> = {
  ready: "waiting",
  physician: "listening",
  patient: "listening",
  translating: "translating",
  speaking: "speaking",
};

/** The interpreter's voice playing in the room: its own row, so it never reads as the next speaker's state. */
function Speaking({ language }: { language: Language }) {
  return (
    <article className={`${styles.turn} ${styles.interpreter}`} data-testid="speaking" data-language={language}>
      <div className={styles.side} lang={language}>
        <div className={styles.meta}>
          <span className={styles.speaker}>Interpreter</span>
          <span className={styles.lang}>{LANGUAGE_LABELS[language].own}</span>
        </div>
        <Orb mode="speaking" label={ORB_LABEL.speaking} className={styles.pendingOrb} />
      </div>
    </article>
  );
}

function PendingTurn({ p, names, other }: { p: Pending; names: Names; other: (lang: Language) => Language }) {
  const mode = orbMode(p);
  const source = p.language;
  const notice: NoticeKey | null =
    p.stage === "awaiting_readback"
      ? "checkingDose"
      : p.stage === "discarded" || p.stage === "failed"
        ? "pleaseRepeat"
        : null;
  return (
    <article className={`${styles.turn} ${styles.pending} ${styles[p.speaker]}`} data-testid="pending" data-stage={p.stage}>
      <Original speaker={p.speaker} name={nameOf(p.speaker, names)} language={source}>
        {p.sourceText ? (
          <p className={styles.text}>{p.sourceText}</p>
        ) : (
          <Orb mode={mode} label={ORB_LABEL[mode]} className={styles.pendingOrb} />
        )}
      </Original>
      {notice && source && (
        <div className={`${styles.side} ${notice === "checkingDose" ? styles.checking : styles.heldBack}`}>
          <div className={styles.meta}>
            <span className={styles.lang}>{LANGUAGE_LABELS[other(source)].own}</span>
            {notice === "pleaseRepeat" && <NotSpoken />}
          </div>
          <Notice notice={notice} first={other(source)} second={source} />
        </div>
      )}
    </article>
  );
}

export default function SharedScreen() {
  const [focusLatest, setFocusLatest] = useState(false);
  const [captions, setCaptions] = useState<TurnCaption[]>([]);
  const [pending, setPending] = useState<Pending | null>(null);
  const [languages, setLanguages] = useState<{ patient: Language; physician: Language }>({
    patient: "pa-IN",
    physician: "en-CA",
  });
  const [names, setNames] = useState<Names>({ physicianName: null, patientName: null });
  // Only lines heard live: the introduction comes before any turn, and a reconnecting screen skips it.
  const [lines, setLines] = useState<InterpreterLine[]>([]);
  const [speaking, setSpeaking] = useState<VoiceSpeaking | null>(null);
  const [paused, setPaused] = useState(false);
  // ADR-003: only heard live; the simulated call has no state on the server to restore.
  const [interpreter, setInterpreter] = useState<InterpreterPhase | null>(null);
  const callTimers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const bottom = useRef<HTMLDivElement | null>(null);
  // CDR-005: the notice and the latest consent change; CDR-006: the record's integrity.
  const [notice, setNotice] = useState<ConsentNotice | null>(null);
  const [consent, setConsent] = useState<ConsentState | null>(null);
  const [integrity, setIntegrity] = useState<RecordIntegrity | null>(null);
  // CDR-005: the explain-back's state only; CDR-006: corrections, to name a broken correction; CDR-007: the summary.
  const [explainBack, setExplainBack] = useState<ExplainBackState | null>(null);
  const [segments, setSegments] = useState<SegmentHistory[]>([]);
  const captionsRef = useRef<TurnCaption[]>([]);
  const [summary, setSummary] = useState<PatientSummary | null>(null);
  const [summaryStage, setSummaryStage] = useState<ArtefactStatus["stage"] | null>(null);
  const [summaryStale, setSummaryStale] = useState(false);
  // CDR-008: the patient's latest signal, for SIGNAL_SHOWN_MS. A live signal shows for the full time from when it
  // arrives, so a TV whose clock is ahead of the laptop's still shows it; only a snapshot's signal is timed from
  // when it was made, so a TV joining late does not show a stale one.
  const [signal, setSignal] = useState<PatientSignalEntry | null>(null);
  const signalTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // CDR-001 `visit.new`: the visit on screen, so a visit.state for another one starts the screen afresh.
  const shownVisit = useRef<string | null>(null);

  const showSignal = useCallback((entry: PatientSignalEntry, live: boolean) => {
    const left = signalShownFor(entry, live, Date.now());
    if (signalTimer.current) clearTimeout(signalTimer.current);
    if (!(left > 0)) {
      setSignal(null);
      return;
    }
    setSignal(entry);
    signalTimer.current = setTimeout(() => setSignal((s) => (s?.signalId === entry.signalId ? null : s)), left);
  }, []);

  useEffect(
    () => () => {
      if (signalTimer.current) clearTimeout(signalTimer.current);
    },
    [],
  );

  const startCall = useCallback(() => {
    callTimers.current.forEach(clearTimeout);
    setInterpreter("connecting");
    callTimers.current = [
      setTimeout(() => setInterpreter("simulated"), INTERPRETER_CONNECTING_MS),
      setTimeout(() => setInterpreter(null), INTERPRETER_CONNECTING_MS + INTERPRETER_SIMULATED_MS),
    ];
  }, []);

  const closeInterpreter = useCallback(() => {
    callTimers.current.forEach(clearTimeout);
    callTimers.current = [];
    setInterpreter(null);
  }, []);

  useEffect(() => () => callTimers.current.forEach(clearTimeout), []);

  const onEvent = useCallback((event: Envelope) => {
    switch (event.type) {
      case "visit.state": {
        const state = event.payload as VisitStatePublic;
        if (visitChanged(shownVisit, event.visitId)) {
          // A new visit: what the screen kept only from live events goes too, as if it had just connected. The
          // signal notice and the interpreter call are cleared below from the empty snapshot.
          setLines([]);
          setSummaryStage(null);
          if (signalTimer.current) clearTimeout(signalTimer.current);
        }
        setPaused(state.paused);
        setLanguages({ patient: state.patientLanguage, physician: state.physicianLanguage });
        setCaptions(state.turns);
        captionsRef.current = state.turns;
        setExplainBack(state.explainBack ?? null);
        setSegments(state.segments ?? []);
        setSummary(state.summary ?? null);
        setSummaryStale(Boolean(state.summaryStale));
        setNames({ physicianName: state.physicianName ?? null, patientName: state.patientName ?? null });
        setSpeaking(state.speaking ?? null);
        setNotice(state.consentNotice ?? null);
        setConsent(state.consentState ?? null);
        setIntegrity(state.integrity);
        // CDR-008: a screen joining within a few seconds of a signal still shows it.
        const latestSignal = state.signals?.at(-1);
        if (latestSignal) showSignal(latestSignal, false);
        else setSignal(null);
        // CDR-006: a TV joining mid-offer shows it, unless the newest caption already says it; after a dismissal, nothing.
        if (!state.interpreterOpen) closeInterpreter();
        else if (state.turns.at(-1)?.status !== "escalated") setInterpreter((phase) => phase ?? "offered");
        const current = state.currentTurn;
        setPending(
          current
            ? {
                ...current,
                language: current.speaker === "physician" ? state.physicianLanguage : state.patientLanguage,
              }
            : null,
        );
        break;
      }
      case "turn.started": {
        const started = event.payload as TurnStarted;
        setPending({ turnId: started.turnId, speaker: started.speaker, language: started.language, stage: "listening" });
        break;
      }
      case "turn.status": {
        const status = event.payload as TurnStatus;
        setPending((p) => (p && p.turnId === status.turnId ? { ...p, stage: status.stage } : p));
        break;
      }
      case "visit.names":
        setNames(event.payload as Names);
        break;
      case "voice.speaking":
        setSpeaking(event.payload as VoiceSpeaking);
        break;
      case "interpreter.line":
        // Asking again replaces the question rather than stacking a copy of it; a line said during the visit
        // (CDR-008) replaces any earlier one, so the room reads one interpreter line at a time.
        setLines((prev) => {
          const line = event.payload as InterpreterLine;
          const mid = MID_VISIT_LINES.has(line.purpose);
          return [...prev.filter((l) => l.purpose !== line.purpose && !(mid && MID_VISIT_LINES.has(l.purpose))), line];
        });
        break;
      case "patient.signal":
        showSignal(event.payload as PatientSignalEntry, true);
        break;
      case "turn.result": {
        const caption = event.payload as TurnCaption;
        setCaptions((prev) => {
          const next = [...prev.filter((c) => c.turnId !== caption.turnId), caption];
          captionsRef.current = next;
          return next;
        });
        setPending((p) => (p && p.turnId === caption.turnId ? null : p));
        // The physician has answered the signal or the closing check with a turn, so the line has done its work.
        setLines((prev) => prev.filter((l) => !MID_VISIT_LINES.has(l.purpose)));
        break;
      }
      case "visit.paused":
        setPaused(true);
        break;
      case "visit.resumed":
        setPaused(false);
        break;
      case "interpreter.escalation": {
        const { reason } = event.payload as InterpreterEscalation;
        if (reason === "requested") startCall();
        // An uncertain turn already says an interpreter is offered in its own caption; a high-risk mark has none.
        else if (reason === "high_risk") setInterpreter((phase) => phase ?? "offered");
        break;
      }
      case "interpreter.dismissed":
        closeInterpreter();
        break;
      case "consent.changed": {
        const changed = event.payload as ConsentState;
        setConsent(changed);
        // Withdrawn: a turn still being interpreted is discarded, so its row goes at once.
        if (changed.state === "withdrawn") setPending(null);
        break;
      }
      case "record.integrity":
        setIntegrity(event.payload as RecordIntegrity);
        break;
      case "explainback.state":
        setExplainBack(event.payload as ExplainBackState);
        break;
      case "segment.amended": {
        const amended = event.payload as SegmentAmended;
        setSegments((all) =>
          applyAmended(all, amended, (id) => captionsRef.current.find((c) => c.turnId === id) ?? null, event.ts),
        );
        break;
      }
      case "summary.status": {
        const status = event.payload as ArtefactStatus;
        if (status.kind === "summary") setSummaryStage(status.stage);
        break;
      }
      case "summary.ready":
        setSummary(event.payload as PatientSummary);
        setSummaryStage("ready");
        setSummaryStale(false);
        break;
      case "artefacts.stale":
        setSummaryStale((event.payload as ArtefactsStale).summary);
        break;
    }
  }, [startCall, closeInterpreter, showSignal]);

  const { state } = useVisitSocket("screen", onEvent);
  const other = (lang: Language) => (lang === languages.physician ? languages.patient : languages.physician);

  // A block body: newer browsers return a Promise from scrollIntoView, which React would call as a cleanup.
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [captions, pending, lines, speaking, interpreter, paused, consent, explainBack, summary, summaryStage, signal]);

  // CDR-005: until consent is given, and again once it is withdrawn, the notice stands in for "ready".
  const consented = consent?.state === "given";
  const brokenAt = integrity?.status === "broken" ? (integrity.brokenAt ?? null) : null;
  const brokenTurnId = turnOfEntry(brokenAt, segments);
  const where = brokenEntryLabel(
    brokenAt,
    captions.map((c) => c.turnId),
    segments,
    { consent: consent ? [consent.entryId] : [], summary: summary ? [summary.summaryId] : [] },
  );
  const listening = explainBack && (explainBack.state === "listening" || explainBack.state === "checking");
  const summaryShown =
    summary !== null ||
    summaryStage === "generating" ||
    summaryStage === "checking" ||
    summaryStage === "retrying" ||
    summaryStage === "refused";
  const playing = summary ? summaryIndexOf(summary.summaryId, speaking?.speaking ? speaking.speechId : null) : null;
  // The introduction shows before the first caption; a line said during the visit shows after the captions.
  const introductionLines = lines.filter((l) => !MID_VISIT_LINES.has(l.purpose));
  const midVisitLines = lines.filter((l) => MID_VISIT_LINES.has(l.purpose));
  const visibleCaptions = captions.slice(focusLatest ? -1 : -6);

  return (
    <main className={styles.screen}>
      <header className={styles.bar}>
        <span className={styles.title}>Live interpretation</span>
        <span className={styles.visitPair}>
          {LANGUAGE_LABELS[languages.patient].own} / {LANGUAGE_LABELS[languages.physician].own}
        </span>
        <div className={styles.barEnd}>
          <button
            type="button"
            className={styles.focusToggle}
            aria-pressed={focusLatest}
            onClick={() => setFocusLatest((active) => !active)}
          >
            Focus latest
          </button>
          <RecordBadge
            integrity={integrity}
            where={where}
            className={styles.badge}
          />
          <span className={styles.status} data-testid="connection" data-state={state}>
            {STATE_LABEL[state]}
          </span>
        </div>
      </header>
      <div>
        {/* Off the record: no captions at all, only the notice in both languages, until the visit resumes. */}
        {paused ? (
          <Resting notice="paused" testId="paused" languages={languages} />
        ) : (
          <>
            {captions.length === 0 && introductionLines.slice(focusLatest ? -1 : -3).map((line) => <Line key={line.lineId} line={line} />)}
            {visibleCaptions.map((c) => (
              <Caption
                key={c.turnId}
                c={c}
                names={names}
                broken={c.turnId === brokenTurnId}
                patient={languages.patient}
              />
            ))}
            {signal && (
              <SignalRow
                entry={signal}
                name={names.patientName ?? null}
                patient={languages.patient}
                physician={languages.physician}
              />
            )}
            {midVisitLines.map((line) => (
              <Line key={line.lineId} line={line} />
            ))}
            {interpreter && (
              <InterpreterNotice phase={interpreter} patient={languages.patient} physician={languages.physician} />
            )}
            {!consented && notice && <ConsentNoticeRow notice={notice} />}
            {consented && listening && (
              <ExplainBackPrompt state={explainBack.state} patient={languages.patient} physician={languages.physician} />
            )}
            {summaryShown && (
              <SummaryRow
                summary={summary}
                stage={summaryStage}
                stale={summaryStale}
                playing={playing}
                patient={languages.patient}
                physician={languages.physician}
              />
            )}
            {speaking?.speaking && <Speaking language={speaking.language} />}
            {consented && pending && <PendingTurn p={pending} names={names} other={other} />}
            {consented &&
              !interpreter &&
              !pending &&
              !speaking?.speaking &&
              captions.length === 0 &&
              lines.length === 0 && <Resting notice="ready" testId="ready" languages={languages} />}
          </>
        )}
        <div ref={bottom} />
      </div>
    </main>
  );
}
