/**
 * The record-verified badge: "Record verified" while the visit's hash chain checks out, and "Record broken",
 * naming the first altered entry, when it does not. Sized in em, so it takes the scale of the bar it sits in
 * (the TV header or the controller header). Shows nothing until the record has its first entry.
 *
 * @implements IDR-003: SHA-256 hash chain for the record-verified badge
 * @implements CDR-006: Record chain entries, review corrections, interpreter dismissal, and presenter controls
 * @contract ws:/ws/visit record.integrity
 */

import type { RecordIntegrity } from "@/lib/contracts";
import styles from "./record.module.css";

export default function RecordBadge({
  integrity,
  where,
  className,
}: {
  integrity: RecordIntegrity | null;
  /** The altered entry in words, for example "turn 3", when the record is broken. */
  where?: string | null;
  className?: string;
}) {
  if (!integrity || (integrity.status === "verified" && !integrity.headHash)) return null;
  const broken = integrity.status === "broken";
  return (
    <span
      className={`${styles.badge} ${broken ? styles.broken : ""} ${className ?? ""}`}
      data-testid="record-badge"
      data-status={integrity.status}
      data-broken-at={integrity.brokenAt ?? undefined}
      title={integrity.headHash ? `Record head ${integrity.headHash.slice(0, 12)}` : undefined}
      role="status"
    >
      {broken ? "Record broken" : "Record verified"}
      {broken && where && <span className={styles.where}> · {where}</span>}
    </span>
  );
}
