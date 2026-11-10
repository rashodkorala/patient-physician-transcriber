"use client";

/**
 * The physician's record view (/record, controller role, never on the TV): the draft clinical note with one
 * provenance tag per sentence, each sentence linked to the turns and versions it was made from, the turns the
 * note could not use, the tags the check downgraded, and a stale mark once the record has grown. The source
 * transcript beside it marks the presenter's injected turns (TDM-002) and the entry the tamper control altered
 * (TDM-005). It plays no audio and reports no voice: only /control speaks.
 *
 * @implements CDR-007: Clinical note with provenance and patient summary on the visit channel
 * @implements CDR-006: Record chain entries, review corrections, interpreter dismissal, and presenter controls
 * @implements ADR-011: Explain-back, note, and summary: frozen sources, model proposes, code checks provenance and values
 * @implements TDM-002: Presenter mismatch control for the blocked-dose beat
 * @implements TDM-005: Hidden record-tamper control for the demo
 * @implements IDR-003: SHA-256 hash chain for the record-verified badge
 * @contract ws:/ws/visit
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  ArtefactsStale,
  ArtefactStatus,
  ClinicalNote,
  ConsentState,
  DemoInjectionState,
  Envelope,
  ErrorPayload,
  EscalationEntry,
  Names,
  NoteSentence,
  ProvenanceTag,
  RecordIntegrity,
  SegmentAmended,
  SegmentHistory,
  Speaker,
  TamperState,
  TurnResult,
  TurnStarted,
  VisitStateController,
} from "@/lib/contracts";
import { LANGUAGE_LABELS } from "@/lib/languages";
import { applyAmended, brokenEntryLabel, captionOf, effective, resolveSources, turnOfEntry, versionOf } from "@/lib/record";
import { useVisitSocket } from "@/lib/socket";
import RecordBadge from "./RecordBadge";
import styles from "./recordView.module.css";

type ControllerState = VisitStateController;

const TAG_TEXT: Record<ProvenanceTag, string> = {
  patient_stated: "Patient-stated",
  physician_stated: "Physician-stated",
  companion_stated: "Companion-stated",
  interpreter_stated: "Interpreter-stated",
  ai_inference: "AI inference",
};

const STAGE_TEXT: Record<ArtefactStatus["stage"], string> = {
  generating: "Writing the note from the frozen record",
  checking: "Checking every tag and source",
  retrying: "A check failed; retrying once with the problems named",
  ready: "Ready",
  failed: "Not published: the note failed its checks twice",
  refused: "Refused",
};

const SPEAKER_LABEL: Record<Speaker, string> = { physician: "Physician", patient: "Patient", companion: "Companion" };

function clock(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function statusWords(turn: TurnResult): string | null {
  if (turn.status === "blocked") return "blocked, not spoken";
  if (turn.status === "escalated") return "escalated, not spoken";
  return null;
}

export default function RecordView() {
  const [turns, setTurns] = useState<TurnResult[]>([]);
  const [segments, setSegments] = useState<SegmentHistory[]>([]);
  const [names, setNames] = useState<Names>({ physicianName: null, patientName: null });
  const [note, setNote] = useState<ClinicalNote | null>(null);
  const [noteStale, setNoteStale] = useState(false);
  const [status, setStatus] = useState<ArtefactStatus | null>(null);
  const [integrity, setIntegrity] = useState<RecordIntegrity | null>(null);
  const [consent, setConsent] = useState<ConsentState | null>(null);
  const [escalations, setEscalations] = useState<EscalationEntry[]>([]);
  const [injected, setInjected] = useState<Set<string>>(new Set());
  const [tamper, setTamper] = useState<TamperState | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const turnsRef = useRef<TurnResult[]>([]);
  const lastStarted = useRef<string | null>(null);
  const sourceList = useRef<HTMLOListElement | null>(null);

  const onEvent = useCallback((event: Envelope) => {
    switch (event.type) {
      case "visit.state": {
        const state = event.payload as ControllerState;
        setTurns(state.turns);
        turnsRef.current = state.turns;
        setSegments(state.segments ?? []);
        setNames({ physicianName: state.physicianName ?? null, patientName: state.patientName ?? null });
        setNote(state.note ?? null);
        setNoteStale(Boolean(state.noteStale));
        setIntegrity(state.integrity);
        setConsent(state.consentState ?? null);
        setEscalations(state.escalations ?? []);
        setInjected(new Set(state.injection?.injectedTurnIds ?? []));
        setTamper(state.tamper ?? null);
        break;
      }
      case "turn.started":
        lastStarted.current = (event.payload as TurnStarted).turnId;
        break;
      case "turn.analysis": {
        const result = event.payload as TurnResult;
        setTurns((prev) => {
          const next = [...prev.filter((t) => t.turnId !== result.turnId), result];
          turnsRef.current = next;
          return next;
        });
        break;
      }
      case "demo.injection_state": {
        // Fired while the turn that carries it is being translated: the one started last.
        const turnId = lastStarted.current;
        if ((event.payload as DemoInjectionState).state === "fired" && turnId) {
          setInjected((all) => new Set(all).add(turnId));
        }
        break;
      }
      case "demo.tamper_state":
        setTamper(event.payload as TamperState);
        break;
      case "record.integrity":
        setIntegrity(event.payload as RecordIntegrity);
        break;
      case "consent.changed":
        setConsent(event.payload as ConsentState);
        break;
      case "visit.names":
        setNames(event.payload as Names);
        break;
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
      case "note.status": {
        const next = event.payload as ArtefactStatus;
        if (next.kind !== "note") break;
        setStatus(next);
        if (next.stage !== "failed") setError(null);
        break;
      }
      case "note.ready":
        setNote(event.payload as ClinicalNote);
        setNoteStale(false);
        setSelected(null);
        break;
      case "artefacts.stale":
        setNoteStale((event.payload as ArtefactsStale).note);
        break;
      case "error": {
        const payload = event.payload as ErrorPayload;
        if (payload.command === "note.generate") setError(payload.message);
        break;
      }
    }
  }, []);

  const { state, send } = useVisitSocket("controller", onEvent);

  const working = status && (status.stage === "generating" || status.stage === "checking" || status.stage === "retrying");
  const sentences = note?.sections.flatMap((s) => s.sentences) ?? [];
  const chosen: NoteSentence | null = sentences.find((s) => s.sentenceId === selected) ?? null;
  const chosenSources = chosen ? resolveSources(chosen.sources, turns, segments) : [];
  const cited = new Map(chosenSources.map((s) => [s.turn.turnId, s.version.version]));
  const downgrades = new Map((note?.tagDowngrades ?? []).map((d) => [d.sentenceId, d.from]));
  const gaps = new Set(note?.untranslatedTurnIds ?? []);
  const brokenAt = integrity?.status === "broken" ? (integrity.brokenAt ?? null) : null;
  const brokenTurn = turnOfEntry(brokenAt, segments);
  const tamperedTurn = turnOfEntry(tamper?.entryId, segments);
  const where = brokenEntryLabel(
    brokenAt,
    turns.map((t) => t.turnId),
    segments,
    { consent: consent ? [consent.entryId] : [], interpreter: escalations.map((e) => e.entryId) },
  );
  const turnNumber = (turnId: string) => turns.findIndex((t) => t.turnId === turnId) + 1;

  // Bring the first source turn into view in the source panel when a sentence is chosen.
  useEffect(() => {
    if (!chosen) return;
    const first = chosen.sources.find((s) => s.kind === "turn");
    if (!first) return;
    sourceList.current
      ?.querySelector(`[data-turn-id="${CSS.escape(first.id)}"]`)
      ?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [chosen]);

  const sourceLines = (turn: TurnResult, version: string) => {
    const history = segments.find((h) => h.segmentId === turn.turnId);
    const v = versionOf(turn, history, version) ?? effective(turn, history);
    return { v, history };
  };

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Physician record · never shown on the shared screen</p>
          <h1>Clinical note</h1>
        </div>
        <div className={styles.headerStatus}>
          <RecordBadge integrity={integrity} where={where} className={styles.badge} />
          <span className={`${styles.status} ${styles[state]}`} data-testid="connection">
            {state}
          </span>
        </div>
      </header>

      <div className={styles.toolbar}>
        <div className={styles.meta}>
          {note ? (
            <p className={styles.aside} data-testid="note-meta">
              Draft for the physician to review and sign · written {clock(note.generatedAt)} from record head{" "}
              <code>{note.basedOnHead.slice(0, 10)}</code>
            </p>
          ) : (
            <p className={styles.aside}>No note yet. It is written from the settled, spoken turns only.</p>
          )}
          {working && (
            <p className={styles.working} data-testid="note-status" data-stage={status.stage} aria-live="polite">
              {STAGE_TEXT[status.stage]}
            </p>
          )}
          {status?.stage === "failed" && (
            <p className={styles.problem} data-testid="note-status" data-stage="failed" role="status">
              {STAGE_TEXT.failed}
              {status.detail && `: ${status.detail}`}
            </p>
          )}
          {error && (
            <p className={styles.problem} role="status" data-testid="note-error">
              {error}
            </p>
          )}
        </div>
        <button
          className={note ? styles.secondary : styles.primary}
          data-testid="note-generate"
          disabled={state !== "open" || Boolean(working)}
          onClick={() => send("note.generate", {})}
        >
          {note ? "Regenerate note" : "Generate note"}
        </button>
      </div>

      {note && noteStale && (
        <p className={styles.stale} data-testid="note-stale" role="status">
          Stale: the record grew after this note was written. Regenerate to include the newer entries.
        </p>
      )}

      <div className={styles.layout}>
        <section className={styles.note} aria-label="Clinical note" data-testid="note">
          {note?.sections.map((section) => (
            <div key={section.heading} className={styles.noteSection}>
              <h2 className={styles.eyebrow}>{section.heading}</h2>
              <ol className={styles.sentences}>
                {section.sentences.map((s) => {
                  const isChosen = s.sentenceId === selected;
                  const resolved = isChosen ? chosenSources : resolveSources(s.sources, turns, segments);
                  return (
                    <li key={s.sentenceId}>
                      <button
                        className={`${styles.sentence} ${isChosen ? styles.chosen : ""} ${s.tag === "ai_inference" ? styles.inference : ""}`}
                        data-testid="note-sentence"
                        data-sentence-id={s.sentenceId}
                        data-tag={s.tag}
                        aria-pressed={isChosen}
                        onClick={() => setSelected(isChosen ? null : s.sentenceId)}
                      >
                        <span className={styles.sentenceText}>{s.text}</span>
                        <span className={styles.sentenceMeta}>
                          <span className={`${styles.tag} ${styles[s.tag]}`} data-testid="note-tag">
                            {TAG_TEXT[s.tag]}
                          </span>
                          {downgrades.has(s.sentenceId) && (
                            <span className={styles.downgrade} data-testid="tag-downgrade">
                              tagged {TAG_TEXT[downgrades.get(s.sentenceId) as ProvenanceTag]?.toLowerCase() ?? downgrades.get(s.sentenceId)}{" "}
                              by the model; the check changed it
                            </span>
                          )}
                          <span className={styles.sourceLinks} data-testid="note-source-links">
                            {resolved.map((r) => (
                              <span key={`${r.ref.id}-${r.ref.version}`} className={styles.sourceLink}>
                                turn {r.index + 1}
                                {r.version.corrected && ", corrected"}
                              </span>
                            ))}
                            {s.sources.some((r) => r.kind === "interpreter_line") && (
                              <span className={styles.sourceLink}>interpreter</span>
                            )}
                          </span>
                        </span>
                      </button>
                      {/* On a narrow screen the sources open under the sentence instead of in the side panel. */}
                      {isChosen && (
                        <div className={styles.inlineSources} data-testid="inline-sources">
                          {resolved.map((r) => (
                            <div key={`${r.ref.id}-${r.ref.version}`} className={styles.inlineSource}>
                              <span className={styles.eyebrow}>
                                Turn {r.index + 1} · {SPEAKER_LABEL[r.turn.speaker]}
                                {r.version.corrected && " · corrected by the patient"}
                              </span>
                              <p lang={r.turn.sourceLanguage}>{r.version.sourceText}</p>
                              <p lang={r.turn.targetLanguage} className={styles.muted}>
                                {r.version.translation}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </li>
                  );
                })}
              </ol>
            </div>
          ))}
          {note && gaps.size > 0 && (
            <div className={styles.gaps} data-testid="note-gaps">
              <h2 className={styles.eyebrow}>Not in the note · never translated</h2>
              <ul>
                {[...gaps].map((id) => {
                  const turn = turns.find((t) => t.turnId === id);
                  return (
                    <li key={id} data-testid="note-gap" data-turn-id={id}>
                      Turn {turnNumber(id) || "?"}
                      {turn && ` · ${SPEAKER_LABEL[turn.speaker]} · ${statusWords(turn) ?? turn.status}`}
                      {turn && <span className={styles.gapText}> “{turn.sourceText}”</span>}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
          {!note && turns.length > 0 && !working && (
            <p className={styles.empty}>Generate the note once the visit has ended and no read-back is waiting.</p>
          )}
        </section>

        <aside className={styles.panel} aria-label="Source turns">
          <h2 className={styles.eyebrow}>Sources · the visit as recorded</h2>
          {turns.length === 0 && <p className={styles.aside}>Nothing said yet.</p>}
          <ol className={styles.turns} ref={sourceList}>
            {turns.map((t, i) => {
              const version = cited.get(t.turnId);
              const { v, history } = sourceLines(t, version ?? currentVersion(segments, t.turnId));
              const unspoken = t.status === "blocked" || t.status === "escalated";
              const wasInjected = injected.has(t.turnId);
              const tampered = tamperedTurn === t.turnId;
              const broken = brokenTurn === t.turnId;
              return (
                <li
                  key={t.turnId}
                  data-testid="source-turn"
                  data-turn-id={t.turnId}
                  data-selected={version !== undefined || undefined}
                  data-injected={wasInjected || undefined}
                  data-tampered={tampered || undefined}
                  data-gap={gaps.has(t.turnId) || undefined}
                  className={`${version !== undefined ? styles.selected : ""} ${broken ? styles.broken : ""}`}
                >
                  <div className={styles.turnHead}>
                    <span className={styles.number}>{i + 1}</span>
                    <span className={`${styles.speaker} ${styles[t.speaker]}`}>
                      {SPEAKER_LABEL[t.speaker]}
                      {t.speaker === "patient" && names.patientName && ` · ${names.patientName}`}
                      {t.speaker === "physician" && names.physicianName && ` · ${names.physicianName}`}
                    </span>
                    {unspoken && <span className={`${styles.tag} ${styles.stop}`}>{statusWords(t)}</span>}
                    {v.corrected && <span className={styles.tag}>corrected by the patient</span>}
                    {wasInjected && (
                      <span className={`${styles.tag} ${styles.stop}`} data-testid="injected">
                        presenter mismatch
                      </span>
                    )}
                    {tampered && (
                      <span className={`${styles.tag} ${styles.stop}`} data-testid="tampered">
                        altered by the presenter&rsquo;s tamper control
                      </span>
                    )}
                    {broken && (
                      <span className={`${styles.tag} ${styles.stop}`} data-testid="record-broken-here">
                        record broken here
                      </span>
                    )}
                  </div>
                  <p className={styles.line} lang={t.sourceLanguage}>
                    {v.sourceText}
                  </p>
                  <p className={`${styles.line} ${styles.translation} ${unspoken ? styles.unspoken : ""}`} lang={t.targetLanguage}>
                    {v.translation}
                  </p>
                  {v.corrected && (
                    <p className={styles.original}>
                      Original · <span lang={t.sourceLanguage}>{t.sourceText}</span>
                    </p>
                  )}
                  {!v.corrected && history && history.amendments.length > 0 && (
                    <p className={styles.original}>Corrected later by the patient; the note cites the original.</p>
                  )}
                  {wasInjected && (
                    <p className={styles.analysis}>
                      The presenter injected this mismatch (TDM-002): the dose was multiplied by 10 after translation, on
                      both attempts.
                    </p>
                  )}
                  {tampered && tamper && (
                    <p className={styles.analysis} data-testid="tamper-note">
                      Changed in place at {clock(tamper.at)} without rehashing, so the record check names it (TDM-005).
                    </p>
                  )}
                  <p className={styles.langs}>
                    {LANGUAGE_LABELS[t.sourceLanguage].own} → {LANGUAGE_LABELS[t.targetLanguage].own}
                  </p>
                </li>
              );
            })}
          </ol>
        </aside>
      </div>
    </main>
  );
}

/** The version a turn is shown at when no sentence cites it: its current one. */
function currentVersion(segments: SegmentHistory[], turnId: string): string {
  return segments.find((h) => h.segmentId === turnId)?.current ?? "original";
}

