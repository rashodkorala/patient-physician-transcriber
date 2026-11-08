"use client";

/**
 * Shared TV screen: large side-by-side captions. Receives only public events.
 *
 * @implements CDR-001: Visit WebSocket event contract
 * @implements CDR-002: Turn result schema
 * @implements CDR-003: Participant names and interpreter lines on the visit channel
 * @implements CDR-004: Interpreter voice playback on the visit channel
 * @contract TurnCaption
 */

import { type ReactNode, useCallback, useEffect, useRef, useState } from "react";
import type {
  Envelope,
  InterpreterLine,
  Language,
  Names,
  Speaker,
  TurnCaption,
  TurnStarted,
  TurnStatus,
  VisitStatePublic,
  VoiceSpeaking,
} from "@/lib/contracts";
import { bilingual, type NoticeKey } from "@/lib/i18n";
import { LANGUAGE_LABELS } from "@/lib/languages";
import { type ConnectionState, useVisitSocket } from "@/lib/socket";
import Highlighted from "./Highlighted";
import Orb, { type OrbMode } from "./Orb";
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
  children,
}: {
  speaker: Speaker;
  name?: string | null;
  language?: Language;
  children: ReactNode;
}) {
  return (
    <div className={styles.side} lang={language}>
      <div className={styles.meta}>
        <span className={`${styles.speaker} ${styles[speaker]}`}>{SPEAKER_LABEL[speaker]}</span>
        {name && (
          <span className={styles.name} data-testid="speaker-name">
            {name}
          </span>
        )}
        {language && <span className={styles.lang}>{LANGUAGE_LABELS[language].own}</span>}
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

function nameOf(speaker: Speaker, names: Names): string | null {
  if (speaker === "physician") return names.physicianName ?? null;
  if (speaker === "patient") return names.patientName ?? null;
  return null;
}

function Caption({ c, names }: { c: TurnCaption; names: Names }) {
  const spoken = c.status === "final" && c.translation !== null;
  return (
    <article className={styles.turn} data-testid="caption" data-turn-id={c.turnId} data-status={c.status}>
      <Original speaker={c.speaker} name={nameOf(c.speaker, names)} language={c.sourceLanguage}>
        <p className={styles.text}>
          <Highlighted text={c.sourceText} values={c.criticalValues.map((v) => v.source)} className={styles.value} />
        </p>
      </Original>
      <div className={styles.side} lang={spoken ? c.targetLanguage : undefined}>
        <div className={styles.meta}>
          <span className={styles.lang}>{LANGUAGE_LABELS[c.targetLanguage].own}</span>
          {spoken && c.toneLabel && (
            <span className={styles.tag} data-testid="tone-label">
              {c.toneLabel}
            </span>
          )}
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
          <Notice
            notice={c.status === "escalated" ? "interpreterOffered" : "pleaseRepeat"}
            first={c.targetLanguage}
            second={c.sourceLanguage}
          />
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
    <article className={`${styles.turn} ${styles.pending}`} data-testid="pending" data-stage={p.stage}>
      <Original speaker={p.speaker} name={nameOf(p.speaker, names)} language={source}>
        {p.sourceText ? (
          <p className={styles.text}>{p.sourceText}</p>
        ) : (
          <Orb mode={mode} label={ORB_LABEL[mode]} className={styles.pendingOrb} />
        )}
      </Original>
      {notice && source && (
        <div className={styles.side}>
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
  const bottom = useRef<HTMLDivElement | null>(null);

  const onEvent = useCallback((event: Envelope) => {
    switch (event.type) {
      case "visit.state": {
        const state = event.payload as VisitStatePublic;
        setLanguages({ patient: state.patientLanguage, physician: state.physicianLanguage });
        setCaptions(state.turns);
        setNames({ physicianName: state.physicianName ?? null, patientName: state.patientName ?? null });
        setSpeaking(state.speaking ?? null);
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
        // Asking again replaces the question rather than stacking a copy of it.
        setLines((prev) => {
          const line = event.payload as InterpreterLine;
          return [...prev.filter((l) => l.purpose !== line.purpose), line];
        });
        break;
      case "turn.result": {
        const caption = event.payload as TurnCaption;
        setCaptions((prev) => [...prev.filter((c) => c.turnId !== caption.turnId), caption]);
        setPending((p) => (p && p.turnId === caption.turnId ? null : p));
        break;
      }
    }
  }, []);

  const { state } = useVisitSocket("screen", onEvent);
  const other = (lang: Language) => (lang === languages.physician ? languages.patient : languages.physician);

  // A block body: newer browsers return a Promise from scrollIntoView, which React would call as a cleanup.
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [captions, pending, lines, speaking]);

  return (
    <main className={styles.screen}>
      <header className={styles.bar}>
        <span className={styles.eyebrow}>Live interpretation</span>
        <span className={styles.visitPair}>
          {LANGUAGE_LABELS[languages.patient].own} / {LANGUAGE_LABELS[languages.physician].own}
        </span>
        <span className={styles.status} data-testid="connection" data-state={state}>
          {STATE_LABEL[state]}
        </span>
      </header>
      <div>
        {captions.length === 0 && lines.slice(-3).map((line) => <Line key={line.lineId} line={line} />)}
        {captions.slice(-6).map((c) => (
          <Caption key={c.turnId} c={c} names={names} />
        ))}
        {speaking?.speaking && <Speaking language={speaking.language} />}
        {pending && <PendingTurn p={pending} names={names} other={other} />}
        {!pending && !speaking?.speaking && captions.length === 0 && lines.length === 0 && (
          <div className={styles.ready} data-testid="ready">
            <Orb mode="ready" className={styles.readyOrb} />
            {bilingual("ready", languages.patient, languages.physician).map(({ lang, text }) => (
              <p key={lang} lang={lang}>
                {text}
              </p>
            ))}
          </div>
        )}
        <div ref={bottom} />
      </div>
    </main>
  );
}
