"use client";

/**
 * Shared TV screen: large side-by-side captions. Receives only public events.
 *
 * @implements CDR-001: Visit WebSocket event contract
 * @implements CDR-002: Turn result schema
 * @contract TurnCaption
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { Envelope, Speaker, TurnCaption, TurnStarted, TurnStatus, VisitStatePublic } from "@/lib/contracts";
import { LANGUAGE_LABELS } from "@/lib/languages";
import { useVisitSocket } from "@/lib/socket";
import styles from "./screen.module.css";

interface Pending {
  turnId: string;
  speaker: Speaker;
  stage: string;
}

const SPEAKER_LABEL: Record<Speaker, string> = { physician: "Physician", patient: "Patient", companion: "Companion" };

export default function SharedScreen() {
  const [captions, setCaptions] = useState<TurnCaption[]>([]);
  const [pending, setPending] = useState<Pending | null>(null);
  const bottom = useRef<HTMLDivElement | null>(null);

  const onEvent = useCallback((event: Envelope) => {
    switch (event.type) {
      case "visit.state": {
        const state = event.payload as VisitStatePublic;
        setCaptions(state.turns);
        setPending(state.currentTurn ? { ...state.currentTurn } : null);
        break;
      }
      case "turn.started": {
        const started = event.payload as TurnStarted;
        setPending({ turnId: started.turnId, speaker: started.speaker, stage: "listening" });
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

  useEffect(() => bottom.current?.scrollIntoView({ behavior: "smooth" }), [captions, pending]);

  return (
    <main className={styles.screen}>
      <div className={styles.status} data-testid="connection" data-state={state} aria-label={`connection ${state}`} />
      <div className={styles.captions}>
        {captions.slice(-6).map((c) => (
          <article key={c.turnId} className={`${styles.turn} ${styles[c.speaker]}`} data-testid="caption">
            <header>{SPEAKER_LABEL[c.speaker]}</header>
            <div className={styles.pair}>
              <p lang={c.sourceLanguage}>
                <span className={styles.lang}>{LANGUAGE_LABELS[c.sourceLanguage].own}</span>
                {c.sourceText}
              </p>
              {c.status === "final" && c.translation ? (
                <p lang={c.targetLanguage}>
                  <span className={styles.lang}>{LANGUAGE_LABELS[c.targetLanguage].own}</span>
                  {c.translation}
                  {c.toneLabel && <span className={styles.tone}>{c.toneLabel}</span>}
                </p>
              ) : (
                <p className={styles.notice}>Please repeat · {LANGUAGE_LABELS[c.targetLanguage].own}</p>
              )}
            </div>
          </article>
        ))}
        {pending && (
          <article className={`${styles.turn} ${styles.pending} ${styles[pending.speaker]}`}>
            <header>{SPEAKER_LABEL[pending.speaker]}</header>
            <p className={styles.notice}>{pending.stage === "failed" ? "Please repeat" : "…"}</p>
          </article>
        )}
        <div ref={bottom} />
      </div>
    </main>
  );
}
