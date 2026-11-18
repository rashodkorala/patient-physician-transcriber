"use client";

/**
 * The patient's device (/patient, the review role): a phone or tablet the patient holds through the visit. Before
 * consent, the notice and its button only. After consent: what the doctor just said, large, in the patient's
 * language with how it was said beneath; the patient's own five controls (I did not understand, please speak more
 * slowly, say that again, pause or resume, a human interpreter), the one bold element on the page; then the review
 * content: the transcript, the explain-back prompt, and the summary.
 *
 * The device shows no emotion, no manner of the patient's own words, no nudge, no cue, and no trust data, ever
 * (MDD-005 rule 3, CDR-008): the review role never receives them, and nothing here would render them.
 *
 * @implements MDD-005: Trust across the barrier
 * @implements CDR-001: Visit WebSocket event contract
 * @implements CDR-008: Patient signals, manner, trust updates, companion turns, and the closing check on the visit channel
 * @implements IDR-005: Manner vocabulary and voice delivery
 * @implements ADR-012: Clinic design system
 * @implements CDR-005: Consent and explain-back on the visit channel
 * @implements CDR-006: Record chain entries, review corrections, interpreter dismissal, and presenter controls
 * @implements CDR-009: Patient confirmation of a captured transcript before translation
 * @implements CDR-007: Clinical note with provenance and patient summary on the visit channel
 * @contract ws:/ws/visit
 * @contract TurnCaption
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { CommandRefused, Envelope, PatientSignal, PatientSignalEntry, Speaker } from "@/lib/contracts";
import { type NoticeKey, SIGNAL_KEY, SPEAKER_KEY, mannerLabel } from "@/lib/i18n";
import { visitChanged } from "@/lib/record";
import Highlighted from "./Highlighted";
import {
  Bi,
  ConsentSection,
  ENGLISH,
  ExplainBackPrompt,
  PausedNotice,
  ReviewHeader,
  ReviewMessage,
  ReviewPage,
  SummarySection,
  TranscriptSection,
  useReviewVisit,
} from "./ReviewScreen";
import review from "./review.module.css";
import styles from "./patient.module.css";

/** How long the device says a signal went through, and how long a refusal stays. */
export const SIGNAL_SENT_MS = 3000;
const REFUSED_MS = 6000;

type Refusal = { reason: CommandRefused["reason"]; key: NoticeKey };

/** The line the device shows for a refused signal: busy, nothing to repeat yet, or a plain refusal. */
export function signalRefusalKey(reason: CommandRefused["reason"], signal: PatientSignal | null): NoticeKey {
  if (reason === "busy") return "refusedBusy";
  if (reason === "invalid" && signal === "repeat") return "nothingToRepeat";
  return "refusedGeneric";
}

export default function PatientScreen() {
  // CDR-008: the signal this device last asked for, and what the server said about it.
  const asked = useRef<PatientSignal | null>(null);
  const [sent, setSent] = useState<PatientSignal | null>(null);
  const [refused, setRefused] = useState<Refusal | null>(null);
  const sentTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const refusedTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(
    () => () => {
      clearTimeout(sentTimer.current);
      clearTimeout(refusedTimer.current);
    },
    [],
  );

  // CDR-001 `visit.new`: the visit shown, so a visit.state for another one clears this device's signal feedback.
  const shownVisit = useRef<string | null>(null);

  const onSignalEvent = useCallback((event: Envelope) => {
    switch (event.type) {
      case "visit.state": {
        if (!visitChanged(shownVisit, event.visitId)) break;
        asked.current = null;
        clearTimeout(sentTimer.current);
        clearTimeout(refusedTimer.current);
        setSent(null);
        setRefused(null);
        break;
      }
      case "patient.signal": {
        // Accepted: shown for a moment, then the controls are plain again. Another device's signal is not ours.
        const entry = event.payload as PatientSignalEntry;
        if (asked.current !== entry.signal) break;
        asked.current = null;
        clearTimeout(sentTimer.current);
        clearTimeout(refusedTimer.current);
        setRefused(null);
        setSent(entry.signal);
        sentTimer.current = setTimeout(() => setSent(null), SIGNAL_SENT_MS);
        break;
      }
      case "command.refused": {
        const refusal = event.payload as CommandRefused;
        if (refusal.command !== "patient.signal") break;
        const key = signalRefusalKey(refusal.reason, asked.current);
        asked.current = null;
        clearTimeout(refusedTimer.current);
        setRefused({ reason: refusal.reason, key });
        refusedTimer.current = setTimeout(() => setRefused(null), REFUSED_MS);
        break;
      }
    }
  }, []);

  const visit = useReviewVisit(onSignalEvent);
  const { patient, captions, consented, open, paused, pending, send, transcriptReview } = visit;

  const signal = (which: PatientSignal) => {
    asked.current = which;
    setRefused(null);
    send("patient.signal", { signal: which });
  };

  // What the doctor just said: the newest final physician turn that was spoken in the patient's language.
  const latest = captions.findLast((c) => c.speaker === "physician" && c.status === "final" && c.translation !== null);
  const latestManner = latest ? mannerLabel(latest.manner, patient) : null;
  const stageKey: NoticeKey = pending?.stage === "listening" ? "stageListening" : "stageTranslating";
  const controlsOff = !open || !consented || paused;

  const SIGNALS: { signal: PatientSignal; testId: string }[] = [
    { signal: "not_understood", testId: "signal-not-understood" },
    { signal: "slower", testId: "signal-slower" },
    { signal: "repeat", testId: "signal-repeat" },
  ];

  return (
    <ReviewPage>
      <ReviewHeader visit={visit} />
      <ReviewMessage visit={visit} />
      <ConsentSection visit={visit} />

      {consented && (
        <>
          <PausedNotice visit={visit} />
          {transcriptReview && !paused && (
            <section className={styles.controls} data-testid="patient-transcript-review" aria-labelledby="patient-transcript-title">
              <h2 className={review.heading} id="patient-transcript-title">
                <Bi k="transcriptReviewTitle" patient={patient} />
              </h2>
              <p className={styles.saidText} lang={transcriptReview.language}>{transcriptReview.text}</p>
              <div className={styles.grid}>
                <button className={`${styles.control} ${styles.clarify}`} disabled={!open} data-testid="patient-transcript-confirm"
                  onClick={() => send("transcript.review_resolve", { reviewId: transcriptReview.reviewId, action: "confirm" })}>
                  <Bi k="transcriptReviewConfirm" patient={patient} />
                </button>
                <button className={styles.control} disabled={!open} data-testid="patient-transcript-repeat"
                  onClick={() => send("transcript.review_resolve", { reviewId: transcriptReview.reviewId, action: "repeat" })}>
                  <Bi k="transcriptReviewRepeat" patient={patient} />
                </button>
              </div>
            </section>
          )}

          {/* IDR-005: the translation large, with how the doctor said it beneath; never the patient's own manner. */}
          <section className={styles.latest} data-testid="patient-latest" data-turn-id={latest?.turnId}>
            <h2 className={review.heading}>
              <Bi k="latestTitle" patient={patient} />
            </h2>
            {latest ? (
              <div className={styles.said}>
                <p className={styles.saidText} lang={patient}>
                  <Highlighted
                    text={latest.translation ?? ""}
                    values={latest.criticalValues.map((v) => v.translated)}
                    className={review.value}
                  />
                </p>
                {latestManner && (
                  <p className={styles.manner} data-testid="manner-label" data-manner={latest.manner}>
                    <span lang={patient}>{latestManner}</span>
                    {patient !== ENGLISH && <span lang={ENGLISH}>{mannerLabel(latest.manner, ENGLISH)}</span>}
                  </p>
                )}
              </div>
            ) : (
              !pending && (
                <p className={styles.quiet} data-testid="patient-nothing-yet">
                  <Bi k="ready" patient={patient} />
                </p>
              )
            )}
            {pending && (
              <p className={styles.quiet} data-testid="patient-pending" data-stage={pending.stage} data-speaker={pending.speaker}>
                <Bi k={SPEAKER_KEY[pending.speaker as Speaker]} patient={patient} className={review.inline} />
                <span className={styles.stage}>
                  <Bi k={stageKey} patient={patient} className={review.inline} />
                </span>
              </p>
            )}
          </section>

          {/* CDR-008: the patient's own voice. The one bold element on the page; everything else stays quiet. */}
          <section className={styles.controls} data-testid="patient-controls" aria-label="Your controls">
            <h2 className={review.heading}>
              <Bi k="yourControls" patient={patient} />
            </h2>
            <div className={styles.feedback} aria-live="polite">
              {sent && (
                <p className={styles.sent} data-testid="signal-sent" data-signal={sent}>
                  <Bi k="signalSent" patient={patient} />
                </p>
              )}
              {refused && (
                <p className={styles.refused} data-testid="signal-refused" data-reason={refused.reason}>
                  <Bi k={refused.key} patient={patient} />
                </p>
              )}
            </div>
            <div className={styles.grid}>
              {SIGNALS.map(({ signal: which, testId }) => (
                <button
                  key={which}
                  className={`${styles.control} ${which === "not_understood" ? styles.clarify : ""}`}
                  data-testid={testId}
                  data-signal={which}
                  disabled={controlsOff}
                  onClick={() => signal(which)}
                >
                  <Bi k={SIGNAL_KEY[which].control} patient={patient} />
                </button>
              ))}
              <button
                className={`${styles.control} ${paused ? styles.resume : ""}`}
                data-testid="patient-pause"
                data-paused={paused || undefined}
                disabled={!open || !consented}
                onClick={() => send(paused ? "visit.resume" : "visit.pause", {})}
              >
                <Bi k={paused ? "resume" : "pause"} patient={patient} />
              </button>
              <button
                className={styles.control}
                data-testid="patient-interpreter"
                disabled={controlsOff}
                onClick={() => send("interpreter.request", {})}
              >
                <Bi k="requestInterpreter" patient={patient} />
              </button>
            </div>
          </section>

          <ExplainBackPrompt visit={visit} />
          <SummarySection visit={visit} />
          <TranscriptSection visit={visit} />
        </>
      )}
    </ReviewPage>
  );
}
