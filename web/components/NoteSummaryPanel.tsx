"use client";

/**
 * The controller's after-the-visit section: generate the note (read and followed to its sources in /record) and
 * the patient's summary, which is published only once its value check passes. A refusal and the values it failed
 * on are shown here only; every other screen learns only that the summary is not ready.
 *
 * @implements CDR-007: Clinical note with provenance and patient summary on the visit channel
 * @implements ADR-011: Explain-back, note, and summary: frozen sources, model proposes, code checks provenance and values
 * @contract ws:/ws/visit
 */

import type { ArtefactStatus, ClinicalNote, PatientSummary, SummaryCheck, TurnResult } from "@/lib/contracts";
import styles from "./controller.module.css";

const WORKING: ArtefactStatus["stage"][] = ["generating", "checking", "retrying"];

const STAGE_TEXT: Record<ArtefactStatus["stage"], string> = {
  generating: "Writing from the frozen record",
  checking: "Checking sources and values",
  retrying: "A check failed; retrying once",
  ready: "Ready",
  failed: "Failed its checks twice; not published",
  refused: "Refused by the value check",
};

const PROBLEM_TEXT: Record<SummaryCheck["mismatches"][number]["problem"], string> = {
  changed: "changed",
  missing: "left out",
  unsupported: "not in the record",
};

export default function NoteSummaryPanel({
  open,
  note,
  noteStale,
  noteStatus,
  summary,
  summaryStale,
  summaryStatus,
  summaryChecks,
  turns,
  send,
}: {
  open: boolean;
  note: ClinicalNote | null;
  noteStale: boolean;
  noteStatus: ArtefactStatus | null;
  summary: PatientSummary | null;
  summaryStale: boolean;
  summaryStatus: ArtefactStatus | null;
  summaryChecks: SummaryCheck[];
  turns: TurnResult[];
  send: (type: string, payload: unknown) => void;
}) {
  const noteWorking = noteStatus && WORKING.includes(noteStatus.stage);
  const summaryWorking = summaryStatus && WORKING.includes(summaryStatus.stage);
  const refused = summaryStatus?.stage === "refused";
  // The failed check that caused the refusal: the last one recorded.
  const failedCheck = refused ? summaryChecks.findLast((c) => c.outcome === "failed") : undefined;
  const sentences = summary ? [...summary.sentences].sort((a, b) => a.index - b.index) : [];
  const number = (turnId: string | null) => (turnId ? turns.findIndex((t) => t.turnId === turnId) + 1 : 0);
  const noteCount = note?.sections.reduce((n, s) => n + s.sentences.length, 0) ?? 0;

  return (
    <section className={styles.section} data-testid="artefacts">
      <h2 className={styles.eyebrow}>Note and summary</h2>

      <div className={styles.artefact} data-testid="note-row">
        <div className={styles.artefactHead}>
          <p className={styles.artefactTitle}>Clinical note</p>
          <p className={styles.artefactState} data-testid="note-row-state">
            {noteWorking
              ? STAGE_TEXT[noteStatus.stage]
              : noteStatus?.stage === "failed"
                ? `${STAGE_TEXT.failed}${noteStatus.detail ? `: ${noteStatus.detail}` : ""}`
                : note
                  ? `${noteCount} sentence${noteCount === 1 ? "" : "s"}, each tagged and sourced${noteStale ? ", stale" : ""}`
                  : "Not written yet"}
          </p>
        </div>
        <div className={styles.actions}>
          <button
            className={styles.secondary}
            data-testid="control-note-generate"
            disabled={!open || Boolean(noteWorking)}
            onClick={() => send("note.generate", {})}
          >
            {note ? "Regenerate note" : "Generate note"}
          </button>
          <a className={styles.link} href="/record" target="record" data-testid="record-link">
            Open the record view
          </a>
        </div>
      </div>

      <div className={styles.artefact} data-testid="summary-row" data-state={summary ? "ready" : (summaryStatus?.stage ?? "none")}>
        <div className={styles.artefactHead}>
          <p className={styles.artefactTitle}>Patient summary</p>
          <p className={`${styles.artefactState} ${refused ? styles.signal : ""}`} data-testid="summary-row-state">
            {summaryWorking
              ? STAGE_TEXT[summaryStatus.stage]
              : refused
                ? STAGE_TEXT.refused
                : summary
                  ? `Published in the patient's language${summaryStale ? ", stale" : ""}`
                  : "Not written yet"}
          </p>
        </div>
        {refused && (
          <div className={styles.refusal} data-testid="summary-refusal" role="status">
            <p className={styles.instruction}>
              {summary
                ? "This attempt was not shown or spoken; the patient keeps the earlier summary."
                : "Not shown or spoken to the patient. Regenerate, or explain the plan again."}
            </p>
            {summaryStatus?.detail && (
              <p className={styles.analysis} data-testid="summary-refusal-detail">
                {summaryStatus.detail}
              </p>
            )}
            {failedCheck && failedCheck.mismatches.length > 0 && (
              <table className={styles.values}>
                <thead>
                  <tr>
                    <th scope="col">Value</th>
                    <th scope="col">In the record</th>
                    <th scope="col">In the summary</th>
                  </tr>
                </thead>
                <tbody>
                  {failedCheck.mismatches.map((m, i) => (
                    <tr key={i} className={styles.mismatch} data-testid="summary-mismatch" data-problem={m.problem}>
                      <td>
                        {m.kind}
                        {number(m.sourceTurnId) > 0 && `, turn ${number(m.sourceTurnId)}`}
                      </td>
                      <td>{m.expected}</td>
                      <td>
                        {m.found ?? <em>missing</em>} ({PROBLEM_TEXT[m.problem]})
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
        {summary && (
          <ol className={styles.summaryText} lang={summary.language} data-testid="control-summary">
            {sentences.map((s) => (
              <li key={s.sentenceId}>{s.text}</li>
            ))}
          </ol>
        )}
        <div className={styles.actions}>
          <button
            className={styles.secondary}
            data-testid="summary-generate"
            disabled={!open || Boolean(summaryWorking)}
            onClick={() => send("summary.generate", {})}
          >
            {summary || refused ? "Regenerate summary" : "Generate summary"}
          </button>
          {summary && (
            <>
              <button
                className={styles.secondary}
                data-testid="control-summary-play"
                disabled={!open}
                onClick={() => send("summary.read_aloud", { summaryId: summary.summaryId })}
              >
                Read aloud
              </button>
              <button
                className={styles.quiet}
                data-testid="control-summary-stop"
                disabled={!open}
                onClick={() => send("summary.stop", { summaryId: summary.summaryId })}
              >
                Stop
              </button>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
