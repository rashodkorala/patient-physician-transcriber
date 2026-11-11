/**
 * Pure helpers for the trust layer: the order the controller lists trust updates in, the order turns settled in,
 * the last translation spoken in the patient's language (for "say that again"), and how long the shared screen
 * shows a patient signal. Type imports only, so it is unit-tested with node:test (EDR-002: npm test).
 *
 * @implements MDD-005: Trust across the barrier
 * @implements CDR-008: Patient signals, manner, trust updates, companion turns, and the closing check on the visit channel
 * @see openspec/tdr/cdr/cdr-008-patient-voice-manner-and-trust-events.md
 */

import type { Language, PatientSignalEntry, TrustUpdate, TurnResult } from "./contracts";

/** CDR-008: how long the room sees a patient's signal; a late screen shows one still inside this window. */
export const SIGNAL_SHOWN_MS = 8000;

/**
 * Where a trust update sorts, given the turns in the order they settled: a turn update at its turn's place, a
 * signal just after the turn it followed (first when it followed none). A turn not in `order` sorts last.
 */
function trustKey(update: TrustUpdate, place: Map<string, number>, last: number): [number, number] {
  const at = update.turnId === null ? 0 : (place.get(update.turnId) ?? last);
  return [at, update.signal ? 1 : 0];
}

/**
 * The trust list with `update` inserted at its place in the spoken order, as the server keeps it. A turn's update
 * comes back from the advisor when it is ready, which may be after later turns and signals were listed: it still
 * lands before them. Updates at the same place keep their arrival order.
 */
export function insertTrust(list: TrustUpdate[], update: TrustUpdate, order: string[]): TrustUpdate[] {
  const place = new Map(order.map((turnId, i) => [turnId, i + 1]));
  const last = order.length + 1;
  const [at, kind] = trustKey(update, place, last);
  let index = list.length;
  while (index > 0) {
    const [otherAt, otherKind] = trustKey(list[index - 1], place, last);
    if (otherAt < at || (otherAt === at && otherKind <= kind)) break;
    index -= 1;
  }
  return [...list.slice(0, index), update, ...list.slice(index)];
}

/**
 * The settled turns in the order they settled, rebuilt from a controller snapshot: the spoken turns in the order
 * of the server's trust list (kept in spoken order), and every other settled turn (blocked, escalated, or still
 * waiting for its advisor) just after the latest-placed turn before it in `turns`, since a turn settles after
 * the turns submitted before it. A turn waiting for its read-back has not settled.
 */
export function settledOrder(turns: TurnResult[], trust: TrustUpdate[], pendingReadback: string | null): string[] {
  const order: string[] = [];
  for (const u of trust) if (u.turnId && !u.signal && !order.includes(u.turnId)) order.push(u.turnId);
  let latest = -1;
  for (const turn of turns) {
    if (turn.turnId === pendingReadback) continue;
    let at = order.indexOf(turn.turnId);
    if (at < 0) {
      at = latest + 1;
      order.splice(at, 0, turn.turnId);
    }
    latest = Math.max(latest, at);
  }
  return order;
}

/**
 * The newest translation spoken in `language` in a controller snapshot, for "say that again" after a reload: a
 * final turn, or a confirmed read-back (which, unlike a rejected one, has its own trust update).
 */
export function lastSpokenIn(
  turns: TurnResult[],
  trust: TrustUpdate[],
  order: string[],
  language: Language,
): { text: string; language: Language; speechId: string } | null {
  const updated = new Set(trust.filter((u) => !u.signal && u.turnId).map((u) => u.turnId));
  const byId = new Map(turns.map((t) => [t.turnId, t]));
  for (const turnId of [...order].reverse()) {
    const turn = byId.get(turnId);
    if (!turn || turn.targetLanguage !== language || !turn.translation) continue;
    if (turn.status === "final" || (turn.status === "readback_required" && updated.has(turnId))) {
      return { text: turn.translation, language, speechId: turnId };
    }
  }
  return null;
}

/**
 * How long the shared screen still shows a signal: the full time for a live one, so a screen whose clock is ahead
 * of the server's still shows it; for a snapshot's, what is left of the time from when it was made.
 */
export function signalShownFor(entry: PatientSignalEntry, live: boolean, now: number): number {
  return live ? SIGNAL_SHOWN_MS : SIGNAL_SHOWN_MS - (now - Date.parse(entry.at));
}
