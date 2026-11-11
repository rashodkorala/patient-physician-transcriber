/**
 * Pure helpers for the record: a turn's versions after the patient's corrections, the entry a broken record
 * names, a note sentence's sources, a summary's speech ids, and which blocked turn was repeated by which.
 * Type imports only, so it is unit-tested with node:test (EDR-002: npm test).
 *
 * @implements CDR-006: Record chain entries, review corrections, interpreter dismissal, and presenter controls
 * @implements CDR-007: Clinical note with provenance and patient summary on the visit channel
 * @implements CDR-008: Patient signals, manner, trust updates, companion turns, and the closing check on the visit channel
 * @implements IDR-003: SHA-256 hash chain for the record-verified badge
 */

import type {
  PatientSummary,
  SegmentAmended,
  SegmentHistory,
  SourceRef,
  TurnCaption,
  TurnResult,
} from "./contracts";

/** The fields every turn shape has (TurnCaption on public screens, TurnResult on the controller). */
export interface TurnLike {
  turnId: string;
  speaker: string;
  sourceText: string;
  translation: string | null;
  status: string;
}

export const ORIGINAL = "original";

/** The public projection of a controller's full turn, to start a history from a live correction. */
export function captionOf(turn: TurnResult): TurnCaption {
  return {
    turnId: turn.turnId,
    speaker: turn.speaker,
    sourceLanguage: turn.sourceLanguage,
    targetLanguage: turn.targetLanguage,
    sourceText: turn.sourceText,
    status: turn.status === "readback_required" ? "final" : turn.status,
    translation: turn.translation,
    toneLabel: null,
    glossaryUsed: turn.glossaryUsed,
    criticalValues: turn.criticalValues.map(({ kind, source, translated }) => ({ kind, source, translated })),
    readbackConfirmed: turn.status === "readback_required",
  };
}

/**
 * Applies a live segment.amended to the histories. A correction becomes the current version and keeps every
 * earlier one; a confirmation names the version it confirms. `original` supplies the caption for a turn that
 * has no history yet. Returns a new array; an event for an unknown turn is ignored.
 */
export function applyAmended(
  histories: SegmentHistory[],
  event: SegmentAmended,
  original: (segmentId: string) => TurnCaption | null,
  at: string,
): SegmentHistory[] {
  const found = histories.find((h) => h.segmentId === event.segmentId);
  const caption = found?.original ?? original(event.segmentId);
  if (!caption) return histories;
  const base: SegmentHistory = found ?? {
    segmentId: event.segmentId,
    original: caption,
    amendments: [],
    confirmed: null,
    current: ORIGINAL,
  };
  let next: SegmentHistory = base;
  if (event.action === "amend" && event.amendmentId) {
    if (base.amendments.some((a) => a.amendmentId === event.amendmentId)) return histories;
    next = {
      ...base,
      amendments: [
        ...base.amendments,
        {
          amendmentId: event.amendmentId,
          sourceText: event.newText ?? "",
          translation: event.translation ?? "",
          toneLabel: event.toneLabel ?? "neutral",
          criticalValues: event.criticalValues ?? [],
          at,
          entryId: event.entryId ?? event.amendmentId,
        },
      ],
      current: event.amendmentId,
    };
  } else if (event.action === "confirm" && event.version) {
    next = { ...base, confirmed: { version: event.version, at, entryId: event.entryId ?? "" } };
  } else {
    return histories;
  }
  return found ? histories.map((h) => (h === found ? next : h)) : [...histories, next];
}

/** A turn's words at one version: the original, or a correction by its amendment id. */
export interface Version {
  version: string;
  sourceText: string;
  translation: string | null;
  corrected: boolean;
}

export function versionOf(turn: TurnLike, history: SegmentHistory | undefined, version: string): Version | null {
  if (version === ORIGINAL) {
    return { version, sourceText: turn.sourceText, translation: turn.translation, corrected: false };
  }
  const amendment = history?.amendments.find((a) => a.amendmentId === version);
  if (!amendment) return null;
  return { version, sourceText: amendment.sourceText, translation: amendment.translation, corrected: true };
}

/** The version a turn is read at now: its latest applied correction, else the original. */
export function effective(turn: TurnLike, history: SegmentHistory | undefined): Version {
  return versionOf(turn, history, history?.current ?? ORIGINAL) ?? versionOf(turn, undefined, ORIGINAL)!;
}

/** Whether the current version has been confirmed (a confirmation of an earlier version no longer counts). */
export function isConfirmed(history: SegmentHistory | undefined): boolean {
  return Boolean(history?.confirmed && history.confirmed.version === history.current);
}

/** Every version of a turn, oldest first, for the history view. */
export function versions(turn: TurnLike, history: SegmentHistory | undefined): Version[] {
  return [
    versionOf(turn, undefined, ORIGINAL)!,
    ...(history?.amendments ?? []).map((a) => versionOf(turn, history, a.amendmentId)!),
  ];
}

/** Other recorded entries the broken badge can name, beyond turns and corrections. */
export interface OtherEntries {
  consent?: string[];
  interpreter?: string[];
  explainBack?: string[];
  summary?: string[];
  /** CDR-008: patient signals, chained as entries of kind signal whose entryId is the signalId. */
  signals?: string[];
}

/**
 * The entry record.integrity names as broken, in words: "turn 3" for a turn (numbered as in the turn list),
 * "turn 3, correction" for an applied correction, or what else it is. Null when nothing is broken.
 */
export function brokenEntryLabel(
  brokenAt: string | null | undefined,
  turnIds: string[],
  histories: SegmentHistory[],
  other: OtherEntries = {},
): string | null {
  if (!brokenAt) return null;
  const turn = turnIds.indexOf(brokenAt);
  if (turn >= 0) return `turn ${turn + 1}`;
  const corrected = histories.find((h) => h.amendments.some((a) => a.amendmentId === brokenAt || a.entryId === brokenAt));
  if (corrected) {
    const index = turnIds.indexOf(corrected.segmentId);
    return index >= 0 ? `turn ${index + 1}, correction` : "a correction";
  }
  if (histories.some((h) => h.confirmed?.entryId === brokenAt)) return "a confirmation";
  if (other.consent?.includes(brokenAt)) return "consent";
  if (other.interpreter?.includes(brokenAt)) return "interpreter entry";
  if (other.explainBack?.includes(brokenAt)) return "explain-back";
  if (other.summary?.includes(brokenAt)) return "summary";
  if (other.signals?.includes(brokenAt)) return "a patient signal";
  return "an earlier entry";
}

/** The turn id an entry belongs to: the turn itself, or the turn a correction amends. */
export function turnOfEntry(entryId: string | null | undefined, histories: SegmentHistory[]): string | null {
  if (!entryId) return null;
  const corrected = histories.find((h) => h.amendments.some((a) => a.amendmentId === entryId || a.entryId === entryId));
  return corrected ? corrected.segmentId : entryId;
}

/** A summary sentence's speech id (CDR-007): `{summaryId}.{n}`, n counted from 0. */
export function summarySpeechId(summaryId: string, index: number): string {
  return `${summaryId}.${index}`;
}

/** Every sentence's speech id and text, in reading order. */
export function summaryReading(summary: PatientSummary): { speechId: string; text: string }[] {
  return [...summary.sentences]
    .sort((a, b) => a.index - b.index)
    .map((s) => ({ speechId: summarySpeechId(summary.summaryId, s.index), text: s.text }));
}

/** The sentence index a speech id names, when it belongs to this summary; else null. */
export function summaryIndexOf(summaryId: string, speechId: string | null | undefined): number | null {
  if (!speechId?.startsWith(`${summaryId}.`)) return null;
  const n = Number(speechId.slice(summaryId.length + 1));
  return Number.isInteger(n) && n >= 0 ? n : null;
}

/** A note sentence's sources resolved to the turns and versions they cite; unresolvable refs are dropped. */
export function resolveSources<T extends TurnLike>(
  sources: SourceRef[],
  turns: T[],
  histories: SegmentHistory[],
): { ref: SourceRef; turn: T; index: number; version: Version }[] {
  return sources.flatMap((ref) => {
    if (ref.kind !== "turn") return [];
    const index = turns.findIndex((t) => t.turnId === ref.id);
    if (index < 0) return [];
    const turn = turns[index];
    const version = versionOf(turn, histories.find((h) => h.segmentId === ref.id), ref.version);
    return version ? [{ ref, turn, index, version }] : [];
  });
}

/**
 * Blocked turns and the turn that repeated each one: the next turn by the same speaker that was not itself
 * blocked or escalated. A blocked turn not yet repeated is left out.
 */
export function repeatedBy(turns: TurnLike[]): Map<string, string> {
  const repeated = new Map<string, string>();
  turns.forEach((turn, i) => {
    if (turn.status !== "blocked") return;
    const next = turns.slice(i + 1).find((t) => t.speaker === turn.speaker && t.status !== "blocked" && t.status !== "escalated");
    if (next) repeated.set(turn.turnId, next.turnId);
  });
  return repeated;
}
