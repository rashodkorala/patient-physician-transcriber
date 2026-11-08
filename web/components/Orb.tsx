/**
 * The interpreter's orb on the shared screen: blurred colour blobs turning inside a dark ball.
 * Cool while the physician speaks, warm while the patient or companion speaks, quick and ringed while
 * the turn is translated or checked, both colours with rings moving out while the interpreter speaks, and dim
 * when nothing is happening.
 *
 * @implements ADR-001: Architecture: Python FastAPI server, Next.js front end, shared TV screen client
 * @implements CDR-001: Visit WebSocket event contract
 * @implements CDR-004: Interpreter voice playback on the visit channel
 */

import styles from "./orb.module.css";

export type OrbMode = "ready" | "physician" | "patient" | "translating" | "speaking";

/** Announced only where the orb stands in for text; elsewhere it is decoration beside words that say the same. */
export default function Orb({ mode, label, className }: { mode: OrbMode; label?: string; className?: string }) {
  const announce = label ? { role: "status", "aria-label": label } : { "aria-hidden": true };
  return (
    <span className={`${styles.orb} ${styles[mode]} ${className ?? ""}`} data-testid="orb" data-mode={mode} {...announce}>
      <span className={styles.halo} />
      <span className={styles.ripple} />
      <span className={`${styles.ripple} ${styles.later}`} />
      <span className={styles.ring} />
      <span className={styles.ball}>
        <span className={styles.core}>
          <span className={`${styles.blob} ${styles.b1}`} />
          <span className={`${styles.blob} ${styles.b2}`} />
          <span className={`${styles.blob} ${styles.b3}`} />
          <span className={`${styles.blob} ${styles.b4}`} />
        </span>
        <span className={styles.sheen} />
      </span>
    </span>
  );
}
