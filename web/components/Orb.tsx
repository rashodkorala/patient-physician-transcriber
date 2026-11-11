/**
 * The interpreter's orb on the shared screen: blurred colour blobs turning inside a soft ball on paper.
 * The physician's colour while the physician speaks, the patient's while the patient or companion speaks, quick
 * and ringed in the care colour while the turn is translated or checked, both speakers' colours with rings moving
 * out while the interpreter speaks, and the paper's greys when nothing is happening. The colours are the speaker
 * tokens, so the orb matches the rows beside it.
 *
 * @implements ADR-001: Architecture: Python FastAPI server, Next.js front end, shared TV screen client
 * @implements ADR-012: Clinic design system
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
