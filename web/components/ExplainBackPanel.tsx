"use client";

/**
 * The controller's explain-back section: open it, let the patient explain the plan in ordinary turns, then check
 * or cancel. The result is the physician's alone: each plan item matched, missed, or contradicted, and whether
 * code or the model decided it. The shared and review screens only see that an explain-back is listening.
 *
 * @implements CDR-005: Consent and explain-back on the visit channel
 * @implements ADR-011: Explain-back, note, and summary: frozen sources, model proposes, code checks provenance and values
 * @implements CDR-008: Patient signals, manner, trust updates, companion turns, and the closing check on the visit channel
 * @contract ws:/ws/visit
 */

import type { ExplainBackItem, ExplainBackResult, ExplainBackState, TurnResult } from "@/lib/contracts";
import styles from "./controller.module.css";

const OUTCOME_TEXT: Record<ExplainBackItem["outcome"], string> = {
  matched: "matched",
  missed: "missed",
  contradicted: "contradicted",
};

const KIND_TEXT: Record<ExplainBackItem["kind"], string> = {
  dose: "dose",
  frequency: "frequency",
  medication: "medication",
  number: "number",
  date: "date",
  instruction: "instruction",
  warning: "warning",
  follow_up: "follow-up",
};

// Problems first: what the physician has to re-explain leads the list.
const ORDER: Record<ExplainBackItem["outcome"], number> = { contradicted: 0, missed: 1, matched: 2 };

export default function ExplainBackPanel({
  state,
  results,
  turns,
  ready,
  send,
}: {
  state: ExplainBackState | null;
  results: ExplainBackResult[];
  turns: TurnResult[];
  /** Connected, consented, not paused, and no read-back waiting. */
  ready: boolean;
  send: (type: string, payload: unknown) => void;
}) {
  const open = state && (state.state === "listening" || state.state === "checking");
  const result = results.at(-1) ?? null;
  const number = (turnId: string) => turns.findIndex((t) => t.turnId === turnId) + 1;
  const spokeYet = turns.some((t) => t.speaker === "physician" && (t.status === "final" || t.status === "readback_required"));
  const count = (outcome: ExplainBackItem["outcome"]) => result?.items.filter((i) => i.outcome === outcome).length ?? 0;

  return (
    <section className={styles.section} data-testid="explainback" data-state={state?.state ?? "none"}>
      <h2 className={styles.eyebrow}>Explain-back, private to you</h2>
      {state?.state === "listening" && (
        <p className={styles.listening} data-state="listening" aria-live="polite">
          Listening to the patient&rsquo;s explanation, {state.explanationTurnIds.length} turn
          {state.explanationTurnIds.length === 1 ? "" : "s"} so far
        </p>
      )}
      {state?.state === "checking" && (
        <p className={`${styles.listening} ${styles.pulse}`} data-state="checking" aria-live="polite">
          Checking the explanation against the plan
        </p>
      )}
      {state?.state === "failed" && (
        <p className={styles.instruction} role="status">
          The check failed and nothing was recorded. Start again when ready.
        </p>
      )}
      <div className={styles.actions}>
        {open ? (
          <>
            <button
              className={styles.primary}
              data-testid="explainback-check"
              disabled={state.state !== "listening" || state.explanationTurnIds.length === 0}
              onClick={() => send("explainback.check", { explainBackId: state.explainBackId })}
            >
              Check explanation
            </button>
            <button
              className={styles.secondary}
              data-testid="explainback-cancel"
              disabled={state.state !== "listening"}
              onClick={() => send("explainback.cancel", { explainBackId: state.explainBackId })}
            >
              Cancel
            </button>
          </>
        ) : (
          <button
            className={styles.secondary}
            data-testid="explainback-start"
            disabled={!ready || !spokeYet}
            onClick={() => send("explainback.start", {})}
          >
            {result ? "Start another explain-back" : "Start explain-back"}
          </button>
        )}
        {/* CDR-008 and MDD-005 rule 6: the interpreter asks the patient, in their language, whether anything should
            be explained again; the English is shown here. Not while a read-back waits or the visit is paused. */}
        <button
          className={styles.secondary}
          data-testid="ask-if-clear"
          disabled={!ready}
          onClick={() => send("visit.ask_if_clear", {})}
        >
          Ask if anything is unclear
        </button>
      </div>
      {!open && !result && (
        <p className={styles.aside}>
          {spokeYet
            ? "Ask the patient to explain the plan in their own words, then check it."
            : "Available once you have explained something to the patient."}
        </p>
      )}
      {result && (
        <div className={styles.result} data-testid="explainback-result" data-id={result.explainBackId}>
          <p className={styles.resultHead}>
            <span>{count("matched")} matched</span>
            <span className={count("missed") ? styles.signal : undefined}>{count("missed")} missed</span>
            <span className={count("contradicted") ? styles.signal : undefined}>{count("contradicted")} contradicted</span>
            {result.explanationTurnIds.length > 0 && (
              <span className={styles.resultFrom}>
                from turn{result.explanationTurnIds.length === 1 ? "" : "s"}{" "}
                {result.explanationTurnIds.map(number).filter(Boolean).join(", ")}
              </span>
            )}
          </p>
          <ul className={styles.items}>
            {[...result.items]
              .sort((a, b) => ORDER[a.outcome] - ORDER[b.outcome])
              .map((item) => (
                <li
                  key={item.itemId}
                  data-testid="explainback-item"
                  data-outcome={item.outcome}
                  data-kind={item.kind}
                  data-decided-by={item.decidedBy}
                >
                  <span className={`${styles.tag} ${item.outcome === "matched" ? "" : styles.stop}`}>
                    {OUTCOME_TEXT[item.outcome]}
                  </span>
                  <div className={styles.itemBody}>
                    <p className={styles.itemText}>{item.instruction}</p>
                    <p className={styles.analysis}>
                      {KIND_TEXT[item.kind]}
                      {item.expected && `, expected ${item.expected}`}
                      {item.decidedBy === "code" && `, heard ${item.heard ?? "nothing"}`}
                      {", "}
                      <span data-testid="decided-by">
                        {item.decidedBy === "code" ? "checked by code" : "judged by the model"}
                      </span>
                    </p>
                  </div>
                </li>
              ))}
          </ul>
        </div>
      )}
    </section>
  );
}
