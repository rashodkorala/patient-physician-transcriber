"use client";

/**
 * Physician controller: languages, push-to-talk, typed fallback, turns, and latency.
 *
 * @implements IDR-001: Push-to-talk per speaker instead of diarisation
 * @implements CDR-001: Visit WebSocket event contract
 * @contract ws:/ws/visit
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  Envelope,
  ErrorPayload,
  Language,
  PatientLanguage,
  Speaker,
  TurnCaption,
  TurnResult,
  TurnStarted,
  VisitStateController,
} from "@/lib/contracts";
import { LANGUAGE_LABELS } from "@/lib/languages";
import { type LatencyRow, median, toCsv, totalMs } from "@/lib/latency";
import { useVisitSocket } from "@/lib/socket";
import { type Capture, speak, startCapture } from "@/lib/speech";
import styles from "./controller.module.css";

const PATIENT_LANGUAGES: PatientLanguage[] = ["pa-IN", "fr-CA"];

export default function Controller() {
  const [patientLanguage, setPatientLanguage] = useState<PatientLanguage>("pa-IN");
  const [turns, setTurns] = useState<TurnResult[]>([]);
  const [latency, setLatency] = useState<LatencyRow[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [recording, setRecording] = useState<Speaker | null>(null);
  const [typedSpeaker, setTypedSpeaker] = useState<Speaker>("patient");
  const [typedText, setTypedText] = useState("");
  const capture = useRef<Capture | null>(null);
  // Submits are sequential from this one controller, so turn.started events match them in order.
  const pendingEnds = useRef<number[]>([]);

  const physicianLanguage: Language = "en-CA";
  const languageOf = (speaker: Speaker): Language => (speaker === "physician" ? physicianLanguage : patientLanguage);

  const updateLatency = (turnId: string, patch: Partial<LatencyRow>) =>
    setLatency((rows) => rows.map((r) => (r.turnId === turnId ? { ...r, ...patch } : r)));

  const onEvent = useCallback((event: Envelope) => {
    switch (event.type) {
      case "visit.state": {
        const state = event.payload as VisitStateController;
        setPatientLanguage(state.patientLanguage);
        setTurns(state.turns);
        break;
      }
      case "turn.started": {
        const started = event.payload as TurnStarted;
        const endOfSpeechAt = pendingEnds.current.shift() ?? Date.now();
        setLatency((rows) => [...rows, { turnId: started.turnId, speaker: started.speaker, endOfSpeechAt }]);
        break;
      }
      case "turn.analysis": {
        const result = event.payload as TurnResult;
        setTurns((prev) => [...prev.filter((t) => t.turnId !== result.turnId), result]);
        break;
      }
      case "turn.result": {
        const caption = event.payload as TurnCaption;
        updateLatency(caption.turnId, { resultAt: Date.now() });
        // The public caption is the signal to speak (CDR-002: shown only once spoken).
        if (caption.status === "final" && caption.translation) {
          speak(caption.translation, caption.targetLanguage)
            .then(({ startedAt }) => updateLatency(caption.turnId, { speechStartAt: startedAt }))
            .catch((error: Error) => setNotice(`Not spoken: ${error.message}`));
        }
        break;
      }
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
    pendingEnds.current.push(endOfSpeechAt);
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

  const totals = latency.map(totalMs).filter((v): v is number => v !== undefined);
  const medianMs = median(totals);

  const downloadCsv = () => {
    const url = URL.createObjectURL(new Blob([toCsv(latency)], { type: "text/csv" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: "latency.csv" });
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <h1>Physician controller</h1>
        <span className={styles[state]} data-testid="connection">{state}</span>
      </header>

      <section className={styles.panel}>
        <label>
          Patient language{" "}
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
        <span className={styles.muted}> with English. Fixed once the first turn starts.</span>
      </section>

      <section className={styles.talk}>
        {(["physician", "patient"] as Speaker[]).map((speaker, i) => (
          <button
            key={speaker}
            className={`${styles.talkButton} ${styles[speaker]} ${recording === speaker ? styles.recording : ""}`}
            onPointerDown={() => void pressTalk(speaker)}
            onPointerUp={() => void releaseTalk()}
            onPointerLeave={() => recording === speaker && void releaseTalk()}
          >
            {speaker === "physician" ? "Physician speaking" : "Patient speaking"}
            <small>
              {LANGUAGE_LABELS[languageOf(speaker)].own} · hold or press {i + 1}
            </small>
          </button>
        ))}
      </section>

      <section className={styles.panel}>
        <h2>Typed turn</h2>
        <div className={styles.typed}>
          <select value={typedSpeaker} onChange={(e) => setTypedSpeaker(e.target.value as Speaker)}>
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
          <button data-testid="typed-send" onClick={sendTyped} disabled={state !== "open"}>
            Send
          </button>
        </div>
      </section>

      {notice && <p className={styles.notice} role="status">{notice}</p>}

      <section className={styles.panel}>
        <h2>Turns (private to the physician)</h2>
        <ol className={styles.turns}>
          {turns.map((t) => (
            <li key={t.turnId}>
              <strong>{t.speaker}</strong>: {t.sourceText}
              <div>→ {t.translation}</div>
              <div className={styles.muted}>
                back: {t.backTranslation} · {t.emotion} · certainty {t.certainty} · confidence {t.confidence.toFixed(2)} · {t.status}
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className={styles.panel}>
        <h2>Latency</h2>
        <p>
          Median end of speech to audio: {medianMs === undefined ? "n/a" : `${(medianMs / 1000).toFixed(2)} s`} over {totals.length} turn(s).
          Target under 3 s.
        </p>
        <button onClick={downloadCsv} disabled={!latency.length}>Download CSV</button>
      </section>
    </main>
  );
}
