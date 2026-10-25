"use client";

/**
 * Physician controller: languages, push-to-talk, typed fallback, read-back, nudges, turns, and latency.
 *
 * @implements IDR-001: Push-to-talk per speaker instead of diarisation
 * @implements ADR-003: Human interpreter escalation on low confidence and high-risk moments
 * @implements CDR-001: Visit WebSocket event contract
 * @implements CDR-002: Turn result schema
 * @contract ws:/ws/visit
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  EmpathyNudge,
  Envelope,
  ErrorPayload,
  EscalationReason,
  InterpreterEscalation,
  Language,
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
import { LANGUAGE_LABELS } from "@/lib/languages";
import { type LatencyRow, median, segments, toCsv } from "@/lib/latency";
import { useVisitSocket } from "@/lib/socket";
import { type Capture, speak, startCapture, warmUp } from "@/lib/speech";
import styles from "./controller.module.css";
import Highlighted from "./Highlighted";

const PATIENT_LANGUAGES: PatientLanguage[] = ["pa-IN", "fr-CA"];
const TONE_LABELS: ToneLabel[] = ["respectful", "reassuring", "empathetic", "neutral"];

const REASON_TEXT: Record<EscalationReason, string> = {
  low_confidence: "the translation stayed uncertain after a retry",
  tone_failure: "the tone check failed after a retry",
  high_risk: "this moment was marked high risk",
  requested: "an interpreter was requested",
};

/** What happened to a turn after its analysis, as far as this controller saw it live. */
interface Outcome {
  spoken?: boolean;
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
      return "spoken";
    case "blocked":
      return "blocked, not spoken";
    case "escalated":
      return "escalated, not spoken";
    case "readback_required":
      if (pending) return "waiting for your read-back";
      if (outcome.spoken) return "confirmed and spoken";
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
  const capture = useRef<Capture | null>(null);
  // Submits are sequential from this one controller, so turn.started events match them in order.
  const pendingTimes = useRef<{ endOfSpeechAt: number; submittedAt: number }[]>([]);

  const physicianLanguage: Language = "en-CA";
  const languageOf = (speaker: Speaker): Language => (speaker === "physician" ? physicianLanguage : patientLanguage);

  const updateLatency = (turnId: string, patch: Partial<LatencyRow>) =>
    setLatency((rows) => rows.map((r) => (r.turnId === turnId ? { ...r, ...patch } : r)));
  const updateOutcome = (turnId: string, patch: Outcome) =>
    setOutcomes((all) => ({ ...all, [turnId]: { ...all[turnId], ...patch } }));

  const onEvent = useCallback((event: Envelope) => {
    switch (event.type) {
      case "visit.state": {
        const state = event.payload as VisitStateController;
        setPatientLanguage(state.patientLanguage);
        setTurns(state.turns);
        setPendingReadback(state.pendingReadback ?? null);
        setNudges(state.nudges);
        break;
      }
      case "turn.started": {
        const started = event.payload as TurnStarted;
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
          speak(caption.translation, caption.targetLanguage)
            .then(({ startedAt }) => updateLatency(caption.turnId, { speechStartAt: startedAt }))
            .catch((error: Error) => setNotice(`Not spoken: ${error.message}`));
        }
        break;
      }
      case "interpreter.escalation": {
        const escalation = event.payload as InterpreterEscalation;
        if (escalation.turnId) updateOutcome(escalation.turnId, { escalation: escalation.reason });
        setNotice(`Not spoken: ${REASON_TEXT[escalation.reason]}. Offer a human interpreter.`);
        break;
      }
      case "empathy.nudge":
        setNudges((prev) => [...prev, event.payload as EmpathyNudge]);
        break;
      case "error":
        setNotice((event.payload as ErrorPayload).message);
        break;
    }
  }, []);

  const { state, send } = useVisitSocket("controller", onEvent);

  const submit = (speaker: Speaker, text: string, confidence: number, endOfSpeechAt: number) => {
    if (!text.trim()) {
      setNotice("Nothing was heard. Please try again.");
      return;
    }
    setNotice(null);
    pendingTimes.current.push({ endOfSpeechAt, submittedAt: Date.now() });
    send("turn.submit", { speaker, language: languageOf(speaker), text: text.trim(), recognitionConfidence: confidence });
  };

  const pressTalk = async (speaker: Speaker) => {
    if (recording) return;
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
    const heard = await active.stop();
    submit(speaker, heard.text, heard.confidence, heard.endOfSpeechAt);
  };

  // Open the Azure voices for this visit's languages before the first turn, so speech starts at once.
  useEffect(() => {
    void warmUp([patientLanguage, physicianLanguage]);
  }, [patientLanguage]);

  // Hold 1 for the physician and 2 for the patient.
  useEffect(() => {
    const keyToSpeaker: Record<string, Speaker> = { "1": "physician", "2": "patient" };
    const down = (e: KeyboardEvent) => {
      const speaker = keyToSpeaker[e.key];
      if (speaker && !e.repeat && document.activeElement?.tagName !== "TEXTAREA") void pressTalk(speaker);
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

      <section className={styles.section}>
        <h2 className={styles.eyebrow}>Visit</h2>
        <div className={styles.visit}>
          <label className={styles.field}>
            <span className={styles.fieldLabel}>Patient language</span>
            <select
              value={patientLanguage}
              disabled={turns.length > 0}
              onChange={(e) =>
                send("visit.set_languages", { patientLanguage: e.target.value, physicianLanguage: "en-CA" })
              }
            >
              {PATIENT_LANGUAGES.map((lang) => (
                <option key={lang} value={lang}>
                  {LANGUAGE_LABELS[lang].own} ({LANGUAGE_LABELS[lang].english})
                </option>
              ))}
            </select>
          </label>
          <p className={styles.aside}>With English. Fixed once the first turn starts.</p>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.eyebrow}>Speak</h2>
        <div className={styles.talk}>
          {(["physician", "patient"] as Speaker[]).map((speaker, i) => (
            <button
              key={speaker}
              className={`${styles.talkButton} ${recording === speaker ? styles.recording : ""}`}
              onPointerDown={() => void pressTalk(speaker)}
              onPointerUp={() => void releaseTalk()}
              onPointerLeave={() => recording === speaker && void releaseTalk()}
            >
              <span className={styles.eyebrow}>{recording === speaker ? "Listening" : `Hold or press ${i + 1}`}</span>
              <span className={styles.talkRole}>{speaker === "physician" ? "Physician" : "Patient"}</span>
              <span className={styles.talkLang}>{LANGUAGE_LABELS[languageOf(speaker)].own}</span>
            </button>
          ))}
        </div>
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
          <button className={styles.primary} data-testid="typed-send" onClick={sendTyped} disabled={state !== "open"}>
            Send
          </button>
        </div>
        {notice && (
          <p className={styles.notice} role="status" data-testid="notice">
            {notice}
          </p>
        )}
      </section>

      <section className={styles.section}>
        <h2 className={styles.eyebrow}>Turns · private to the physician</h2>
        {turns.length === 0 && <p className={styles.aside}>Nothing said yet.</p>}
        <ol className={styles.turns}>
          {turns.map((t) => {
            const outcome = outcomes[t.turnId] ?? {};
            const unspoken = t.status === "blocked" || t.status === "escalated" || outcome.discarded;
            return (
              <li key={t.turnId} data-testid="turn" data-status={t.status}>
                <div className={styles.turnHead}>
                  <span className={`${styles.speaker} ${styles[t.speaker]}`}>{t.speaker}</span>
                  <span className={`${styles.tag} ${unspoken ? styles.stop : ""}`}>
                    {statusText(t, outcome, t.turnId === pendingReadback)}
                  </span>
                  {!unspoken && <span className={styles.tag}>{toneLabel(t)}</span>}
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
              </li>
            );
          })}
        </ol>
      </section>

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
    </main>
  );
}
