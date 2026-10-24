"use client";

/**
 * Shared TV screen: large side-by-side captions. Receives only public events.
 *
 * @implements CDR-001: Visit WebSocket event contract
 * @implements CDR-002: Turn result schema
 * @contract TurnCaption
 */

import { type ReactNode, useCallback, useEffect, useRef, useState } from "react";
import type {
  Envelope,
  Language,
  Speaker,
  TurnCaption,
  TurnStarted,
  TurnStatus,
  VisitStatePublic,
} from "@/lib/contracts";
import { bilingual, type NoticeKey } from "@/lib/i18n";
import { LANGUAGE_LABELS } from "@/lib/languages";
import { type ConnectionState, useVisitSocket } from "@/lib/socket";
import Highlighted from "./Highlighted";
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

/** The original, with the speaker label above it. */
function Original({ speaker, language, children }: { speaker: Speaker; language?: Language; children: ReactNode }) {
  return (
    <div className={styles.side} lang={language}>
      <div className={styles.meta}>
        <span className={`${styles.speaker} ${styles[speaker]}`}>{SPEAKER_LABEL[speaker]}</span>
        {language && <span className={styles.lang}>{LANGUAGE_LABELS[language].own}</span>}
      </div>
      {children}
    </div>
  );
}

function NotSpoken() {
  return <span className={`${styles.tag} ${styles.stop}`}>Not spoken</span>;
}

function Caption({ c }: { c: TurnCaption }) {
  const spoken = c.status === "final" && c.translation !== null;
  return (
    <article className={styles.turn} data-testid="caption" data-turn-id={c.turnId} data-status={c.status}>
      <Original speaker={c.speaker} language={c.sourceLanguage}>
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

function PendingTurn({ p, other }: { p: Pending; other: (lang: Language) => Language }) {
  const source = p.language;
  const notice: NoticeKey | null =
    p.stage === "awaiting_readback"
      ? "checkingDose"
      : p.stage === "discarded" || p.stage === "failed"
        ? "pleaseRepeat"
        : null;
  return (
    <article className={`${styles.turn} ${styles.pending}`} data-testid="pending" data-stage={p.stage}>
      <Original speaker={p.speaker} language={source}>
        {p.sourceText ? (
          <p className={styles.text}>{p.sourceText}</p>
        ) : (
          <span className={styles.working} role="status" aria-label="working" />
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
  const bottom = useRef<HTMLDivElement | null>(null);

  const onEvent = useCallback((event: Envelope) => {
    switch (event.type) {
      case "visit.state": {
        const state = event.payload as VisitStatePublic;
        setLanguages({ patient: state.patientLanguage, physician: state.physicianLanguage });
        setCaptions(state.turns);
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

  useEffect(() => bottom.current?.scrollIntoView({ behavior: "smooth" }), [captions, pending]);

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
        {captions.slice(-6).map((c) => (
          <Caption key={c.turnId} c={c} />
        ))}
        {pending && <PendingTurn p={pending} other={other} />}
        <div ref={bottom} />
      </div>
    </main>
  );
}
