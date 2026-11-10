"use client";

/**
 * The patient's review screen (/review, a tablet or phone): consent by the patient's own tap, the bilingual
 * transcript with the patient's own turns to confirm or correct by re-speaking (every original kept in the
 * history), the explain-back prompt with no outcome, and the summary once it has passed its check, read aloud a
 * sentence at a time by the controller's voice. Receives only public events; refusals arrive as command.refused.
 *
 * @implements CDR-005: Consent and explain-back on the visit channel
 * @implements CDR-006: Record chain entries, review corrections, interpreter dismissal, and presenter controls
 * @implements CDR-007: Clinical note with provenance and patient summary on the visit channel
 * @implements IDR-003: SHA-256 hash chain for the record-verified badge
 * @implements TDM-002: Presenter mismatch control for the blocked-dose beat
 * @contract ws:/ws/visit
 * @contract TurnCaption
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  ArtefactsStale,
  ArtefactStatus,
  CommandRefused,
  ConsentNotice,
  ConsentState,
  Envelope,
  ExplainBackState,
  Language,
  Names,
  PatientLanguage,
  PatientSummary,
  RecordIntegrity,
  SegmentAmended,
  SegmentHistory,
  SegmentStatus,
  Speaker,
  TurnCaption,
  VisitStatePublic,
  VoiceSpeaking,
} from "@/lib/contracts";
import { type NoticeKey, notice } from "@/lib/i18n";
import { LANGUAGE_LABELS } from "@/lib/languages";
import {
  applyAmended,
  brokenEntryLabel,
  effective,
  isConfirmed,
  repeatedBy,
  summaryIndexOf,
  turnOfEntry,
  versions,
} from "@/lib/record";
import { type ConnectionState, useVisitSocket } from "@/lib/socket";
import { type Capture, startCapture } from "@/lib/speech";
import Highlighted from "./Highlighted";
import RecordBadge from "./RecordBadge";
import styles from "./review.module.css";

type ReviewState = VisitStatePublic;

const SPEAKER_LABEL: Record<Speaker, string> = { physician: "Physician", patient: "Patient", companion: "Companion" };
const STATE_LABEL: Record<ConnectionState, string> = { open: "Connected", connecting: "Connecting", closed: "Reconnecting" };
const ENGLISH: Language = "en-CA";

/** command.refused carries a reason code only; each maps to a plain line in both languages. */
function refusalKey(reason: CommandRefused["reason"]): NoticeKey {
  if (reason === "busy") return "refusedBusy";
  if (reason === "not_current") return "refusedNotCurrent";
  return "refusedGeneric";
}

function clock(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

/** A label in the patient's language, with English beneath it. */
function Bi({ k, patient, className }: { k: NoticeKey; patient: Language; className?: string }) {
  return (
    <span className={`${styles.bi} ${className ?? ""}`}>
      <span lang={patient}>{notice(k, patient)}</span>
      {patient !== ENGLISH && (
        <span className={styles.biEnglish} lang={ENGLISH}>
          {notice(k, ENGLISH)}
        </span>
      )}
    </span>
  );
}

/** A notice in the patient's language and English, as the interpreter's words. */
function Notice({ k, patient, testId, className }: { k: NoticeKey; patient: Language; testId?: string; className?: string }) {
  return (
    <div className={`${styles.notice} ${className ?? ""}`} data-testid={testId ?? `notice-${k}`}>
      <p lang={patient}>{notice(k, patient)}</p>
      {patient !== ENGLISH && <p lang={ENGLISH}>{notice(k, ENGLISH)}</p>}
    </div>
  );
}

function nameOf(speaker: Speaker, names: Names): string | null {
  if (speaker === "physician") return names.physicianName ?? null;
  if (speaker === "patient") return names.patientName ?? null;
  return null;
}

interface Correction {
  segmentId: string;
  stage: SegmentStatus["stage"];
}

export default function ReviewScreen() {
  const [patient, setPatient] = useState<PatientLanguage>("pa-IN");
  const [captions, setCaptions] = useState<TurnCaption[]>([]);
  const [segments, setSegments] = useState<SegmentHistory[]>([]);
  const [names, setNames] = useState<Names>({ physicianName: null, patientName: null });
  const [consentNotice, setConsentNotice] = useState<ConsentNotice | null>(null);
  const [consent, setConsent] = useState<ConsentState | null>(null);
  const [integrity, setIntegrity] = useState<RecordIntegrity | null>(null);
  const [paused, setPaused] = useState(false);
  const [explainBack, setExplainBack] = useState<ExplainBackState | null>(null);
  const [summary, setSummary] = useState<PatientSummary | null>(null);
  const [summaryStale, setSummaryStale] = useState(false);
  const [summaryStage, setSummaryStage] = useState<ArtefactStatus["stage"] | null>(null);
  const [speaking, setSpeaking] = useState<VoiceSpeaking | null>(null);
  const [correction, setCorrection] = useState<Correction | null>(null);
  const [refusedOn, setRefusedOn] = useState<string | null>(null);
  const [recording, setRecording] = useState<string | null>(null);
  const [message, setMessage] = useState<NoticeKey | null>(null);
  const capture = useRef<Capture | null>(null);
  const captionsRef = useRef<TurnCaption[]>([]);
  const messageTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const say = useCallback((key: NoticeKey | null) => {
    clearTimeout(messageTimer.current);
    setMessage(key);
    if (key) messageTimer.current = setTimeout(() => setMessage(null), 8000);
  }, []);

  useEffect(() => () => clearTimeout(messageTimer.current), []);

  const onEvent = useCallback(
    (event: Envelope) => {
      switch (event.type) {
        case "visit.state": {
          const state = event.payload as ReviewState;
          setPatient(state.patientLanguage);
          setCaptions(state.turns);
          captionsRef.current = state.turns;
          setSegments(state.segments ?? []);
          setNames({ physicianName: state.physicianName ?? null, patientName: state.patientName ?? null });
          setConsentNotice(state.consentNotice ?? null);
          setConsent(state.consentState ?? null);
          setIntegrity(state.integrity);
          setPaused(state.paused);
          setExplainBack(state.explainBack ?? null);
          setSummary(state.summary ?? null);
          setSummaryStale(Boolean(state.summaryStale));
          setSpeaking(state.speaking ?? null);
          break;
        }
        case "turn.result": {
          const caption = event.payload as TurnCaption;
          setCaptions((prev) => {
            const next = [...prev.filter((c) => c.turnId !== caption.turnId), caption];
            captionsRef.current = next;
            return next;
          });
          break;
        }
        case "visit.names":
          setNames(event.payload as Names);
          break;
        case "consent.changed":
          setConsent(event.payload as ConsentState);
          break;
        case "record.integrity":
          setIntegrity(event.payload as RecordIntegrity);
          break;
        case "visit.paused":
          setPaused(true);
          break;
        case "visit.resumed":
          setPaused(false);
          break;
        case "voice.speaking":
          setSpeaking(event.payload as VoiceSpeaking);
          break;
        case "explainback.state":
          setExplainBack(event.payload as ExplainBackState);
          break;
        case "segment.status": {
          const status = event.payload as SegmentStatus;
          if (status.stage === "applied") {
            setCorrection(null);
            setRefusedOn(null);
          } else if (status.stage === "refused") {
            setCorrection(null);
            setRefusedOn(status.segmentId);
          } else {
            setRefusedOn(null);
            setCorrection({ segmentId: status.segmentId, stage: status.stage });
          }
          break;
        }
        case "segment.amended": {
          const amended = event.payload as SegmentAmended;
          // A confirmation or a correction that went through answers an earlier refusal on that turn.
          setRefusedOn((id) => (id === amended.segmentId ? null : id));
          setSegments((all) =>
            applyAmended(all, amended, (id) => captionsRef.current.find((c) => c.turnId === id) ?? null, event.ts),
          );
          break;
        }
        case "summary.status": {
          const status = event.payload as ArtefactStatus;
          if (status.kind !== "summary") break;
          setSummaryStage(status.stage);
          break;
        }
        case "summary.ready":
          setSummary(event.payload as PatientSummary);
          setSummaryStale(false);
          setSummaryStage("ready");
          break;
        case "artefacts.stale":
          setSummaryStale((event.payload as ArtefactsStale).summary);
          break;
        case "command.refused": {
          const refused = event.payload as CommandRefused;
          if (refused.command === "segment.amend") setCorrection(null);
          say(refusalKey(refused.reason));
          break;
        }
      }
    },
    [say],
  );

  const { state, send } = useVisitSocket("review", onEvent);

  const consented = consent?.state === "given";
  const open = state === "open";

  const giveConsent = () =>
    consentNotice && send("consent.give", { noticeVersion: consentNotice.version, language: consentNotice.language });

  /** Re-speak a correction: press to start, press again when done; the words go to the server's turn graph. */
  const toggleCorrection = async (segmentId: string) => {
    if (recording) {
      if (recording !== segmentId) return;
      const active = capture.current;
      capture.current = null;
      setRecording(null);
      if (!active) return;
      try {
        const heard = await active.stop();
        if (!heard.text.trim()) return say("correctionRefused");
        setRefusedOn(null);
        setCorrection({ segmentId, stage: "translating" });
        send("segment.amend", {
          segmentId,
          text: heard.text.trim().slice(0, 1000),
          language: patient,
          recognitionConfidence: Math.max(0, Math.min(1, heard.confidence)),
        });
      } catch {
        say("micUnavailable");
      }
      return;
    }
    say(null);
    setRecording(segmentId);
    try {
      capture.current = await startCapture(patient);
    } catch {
      setRecording(null);
      say("micUnavailable");
    }
  };

  const brokenAt = integrity?.status === "broken" ? (integrity.brokenAt ?? null) : null;
  const brokenTurn = turnOfEntry(brokenAt, segments);
  const where = brokenEntryLabel(
    brokenAt,
    captions.map((c) => c.turnId),
    segments,
    { consent: consent ? [consent.entryId] : [], summary: summary ? [summary.summaryId] : [] },
  );
  const repeats = repeatedBy(captions);
  const playing = summary ? summaryIndexOf(summary.summaryId, speaking?.speaking ? speaking.speechId : null) : null;
  const preparing = summaryStage === "generating" || summaryStage === "checking" || summaryStage === "retrying";

  return (
    <main className={styles.page}>
      <header className={styles.bar}>
        <Bi k="reviewTitle" patient={patient} className={styles.title} />
        <span className={styles.pair}>
          {LANGUAGE_LABELS[patient].own} / {LANGUAGE_LABELS[ENGLISH].own}
        </span>
        <div className={styles.barEnd}>
          <RecordBadge integrity={integrity} where={where} className={styles.badge} />
          <span className={styles.status} data-testid="connection" data-state={state}>
            {STATE_LABEL[state]}
          </span>
        </div>
      </header>

      {message && (
        <div className={styles.message} role="status" data-testid="review-message" data-key={message}>
          <Bi k={message} patient={patient} />
        </div>
      )}

      {/* CDR-005: the patient's own tap; the server records it as given by the patient. */}
      {!consented && consentNotice && (
        <section className={styles.consent} data-testid="review-consent">
          {consentNotice.lines.map(({ language, text }) => (
            <p key={language} lang={language}>
              {text}
            </p>
          ))}
          <button
            className={styles.primary}
            data-testid="review-consent-give"
            disabled={!open}
            onClick={giveConsent}
          >
            <Bi k="consentAgree" patient={patient} />
          </button>
        </section>
      )}

      {paused && <Notice k="paused" patient={patient} testId="review-paused" />}

      {/* CDR-005: a prompt only; the patient never sees what was matched or missed. */}
      {explainBack && (explainBack.state === "listening" || explainBack.state === "checking") && (
        <section className={styles.prompt} data-testid="review-explainback" data-state={explainBack.state}>
          <Notice
            k={explainBack.state === "listening" ? "explainBackListening" : "explainBackChecking"}
            patient={patient}
          />
        </section>
      )}

      {/* CDR-007: shown only once it has passed its value check; a refusal says only that it is not ready. */}
      {(summary || preparing || summaryStage === "refused") && (
        <section className={styles.summary} data-testid="review-summary" data-state={summary ? "ready" : summaryStage}>
          <div className={styles.sectionHead}>
            <h2 className={styles.heading}>
              <Bi k="summaryTitle" patient={patient} />
            </h2>
            {summary && (
              <div className={styles.actions}>
                <button
                  className={styles.primary}
                  data-testid="summary-listen"
                  disabled={!open}
                  onClick={() => send("summary.read_aloud", { summaryId: summary.summaryId })}
                >
                  <Bi k="listen" patient={patient} />
                </button>
                <button
                  className={styles.secondary}
                  data-testid="summary-stop"
                  disabled={!open}
                  onClick={() => send("summary.stop", { summaryId: summary.summaryId })}
                >
                  <Bi k="stop" patient={patient} />
                </button>
              </div>
            )}
          </div>
          {summary ? (
            <>
              {summaryStale && <Notice k="summaryStale" patient={patient} testId="summary-stale" />}
              <ol className={styles.sentences} lang={summary.language}>
                {[...summary.sentences]
                  .sort((a, b) => a.index - b.index)
                  .map((s) => (
                    <li
                      key={s.sentenceId}
                      data-testid="summary-sentence"
                      data-playing={playing === s.index || undefined}
                      className={playing === s.index ? styles.playing : undefined}
                    >
                      <span>
                        <Highlighted
                          text={s.text}
                          values={summary.values.map((v) => v.text)}
                          className={styles.value}
                        />
                      </span>
                    </li>
                  ))}
              </ol>
            </>
          ) : (
            <Notice
              k={summaryStage === "refused" ? "summaryRefused" : "summaryPreparing"}
              patient={patient}
              testId={summaryStage === "refused" ? "summary-refused" : "summary-preparing"}
            />
          )}
        </section>
      )}

      <section className={styles.transcript}>
        <h2 className={styles.heading}>
          <Bi k="transcriptTitle" patient={patient} />
        </h2>
        <ol className={styles.turns}>
          {captions.map((c, i) => {
            const history = segments.find((h) => h.segmentId === c.turnId);
            const now = effective(c, history);
            const mine = c.speaker === "patient" && c.status === "final";
            const spoken = c.status === "final" && now.translation !== null;
            const confirmed = isConfirmed(history);
            const checking = correction?.segmentId === c.turnId;
            const refused = refusedOn === c.turnId;
            const broken = brokenTurn === c.turnId;
            const repeatedAs = repeats.get(c.turnId);
            // The patient's language on the left for every turn: the original for the patient, the
            // spoken translation for the physician.
            const patientSide = c.sourceLanguage === patient ? now.sourceText : spoken ? now.translation : null;
            const englishSide = c.sourceLanguage === patient ? (spoken ? now.translation : null) : now.sourceText;
            const values = c.criticalValues;
            const patientValues = values.map((v) => (c.sourceLanguage === patient ? v.source : v.translated));
            const englishValues = values.map((v) => (c.sourceLanguage === patient ? v.translated : v.source));
            const recordingThis = recording === c.turnId;
            return (
              <li
                key={c.turnId}
                id={`turn-${c.turnId}`}
                className={`${styles.turn} ${broken ? styles.broken : ""}`}
                data-testid="review-turn"
                data-turn-id={c.turnId}
                data-status={c.status}
                data-version={now.version}
                data-confirmed={confirmed || undefined}
                data-broken={broken || undefined}
              >
                <div className={styles.meta}>
                  <span className={styles.number}>{i + 1}</span>
                  <span className={`${styles.speaker} ${styles[c.speaker]}`}>{SPEAKER_LABEL[c.speaker]}</span>
                  {nameOf(c.speaker, names) && <span className={styles.name}>{nameOf(c.speaker, names)}</span>}
                  {!spoken && <span className={`${styles.tag} ${styles.stop}`}>Not spoken</span>}
                  {now.corrected && (
                    <span className={styles.tag} data-testid="corrected">
                      <Bi k="corrected" patient={patient} className={styles.inline} />
                    </span>
                  )}
                  {confirmed && (
                    <span className={styles.tag} data-testid="confirmed">
                      <Bi k="confirmed" patient={patient} className={styles.inline} />
                    </span>
                  )}
                  {broken && (
                    <span className={`${styles.tag} ${styles.stop}`} data-testid="record-broken-here">
                      Record broken here
                    </span>
                  )}
                </div>
                <div className={styles.columns}>
                  <div className={styles.side} lang={patientSide !== null ? patient : undefined}>
                    {patientSide !== null ? (
                      <p className={styles.text}>
                        <Highlighted text={patientSide} values={patientValues} className={styles.value} />
                      </p>
                    ) : repeatedAs ? (
                      // TDM-002: a blocked turn shows no translation and no reason; only that it was said again.
                      <a className={styles.jump} href={`#turn-${repeatedAs}`} data-testid="repeated-link">
                        <Notice k="repeatedBelow" patient={patient} testId="review-unspoken" />
                      </a>
                    ) : (
                      <Notice
                        k={c.status === "escalated" ? "interpreterOffered" : "pleaseRepeat"}
                        patient={patient}
                        testId="review-unspoken"
                      />
                    )}
                  </div>
                  <div className={styles.side} lang={englishSide !== null ? ENGLISH : undefined}>
                    {englishSide !== null && (
                      <p className={`${styles.text} ${styles.english}`}>
                        <Highlighted text={englishSide} values={englishValues} className={styles.value} />
                      </p>
                    )}
                  </div>
                </div>
                {checking && (
                  <p className={styles.checking} data-testid="correction-checking" data-stage={correction?.stage}>
                    <Bi k="correctionChecking" patient={patient} />
                  </p>
                )}
                {refused && (
                  <Notice k="correctionRefused" patient={patient} testId="correction-refused" className={styles.refused} />
                )}
                {mine && consented && (
                  <div className={styles.actions}>
                    {!confirmed && (
                      <button
                        className={styles.secondary}
                        data-testid="review-confirm"
                        disabled={!open || checking || Boolean(recording)}
                        onClick={() => send("segment.confirm", { segmentId: c.turnId, version: now.version })}
                      >
                        <Bi k="confirm" patient={patient} />
                      </button>
                    )}
                    <button
                      className={recordingThis ? styles.recording : styles.secondary}
                      data-testid="review-correct"
                      data-recording={recordingThis || undefined}
                      disabled={!open || paused || Boolean(correction) || (Boolean(recording) && !recordingThis)}
                      onClick={() => void toggleCorrection(c.turnId)}
                    >
                      <Bi k={recordingThis ? "correctStop" : "correct"} patient={patient} />
                    </button>
                  </div>
                )}
                {history && history.amendments.length > 0 && (
                  <details className={styles.history} data-testid="review-history">
                    <summary>
                      <Bi k="history" patient={patient} className={styles.inline} />
                    </summary>
                    <ol>
                      {versions(c, history).map((v) => {
                        const amendment = history.amendments.find((a) => a.amendmentId === v.version);
                        return (
                          <li
                            key={v.version}
                            data-testid="history-version"
                            data-version={v.version}
                            data-current={v.version === history.current || undefined}
                          >
                            <span className={styles.eyebrow}>
                              <Bi k={v.corrected ? "correction" : "original"} patient={patient} className={styles.inline} />
                              {amendment && ` · ${clock(amendment.at)}`}
                              {history.confirmed?.version === v.version && (
                                <>
                                  {" · "}
                                  <Bi k="confirmed" patient={patient} className={styles.inline} />
                                </>
                              )}
                            </span>
                            <p lang={c.sourceLanguage}>{v.sourceText}</p>
                            {v.translation && (
                              <p lang={c.targetLanguage} className={styles.muted}>
                                {v.translation}
                              </p>
                            )}
                          </li>
                        );
                      })}
                    </ol>
                  </details>
                )}
              </li>
            );
          })}
        </ol>
        {captions.length === 0 && consented && <Notice k="ready" patient={patient} testId="review-empty" />}
      </section>
    </main>
  );
}
