/**
 * Per-turn latency log on the controller (task 1.7).
 * End of speech to translated audio starting is the figure that must stay under 3 seconds.
 * It is split into three segments so a slow turn shows where the time went. The physician's own
 * time deciding a dose read-back is never counted.
 */

export interface LatencyRow {
  turnId: string;
  speaker: string;
  /** Talk button released, or a typed turn sent. */
  endOfSpeechAt: number;
  /** Recognised text sent to the server. */
  submittedAt: number;
  /** Server finished the turn (turn.analysis). */
  analysisAt?: number;
  /** Caption released; for a dose, after the physician confirms. */
  resultAt?: number;
  /** Released for speech (final); blocked and escalated turns are never spoken, so never counted. */
  spoken?: boolean;
  speechStartAt?: number;
}

export interface Segments {
  recognitionMs: number;
  serverMs?: number;
  voiceMs?: number;
  totalMs?: number;
}

export function segments(row: LatencyRow): Segments {
  const recognitionMs = row.submittedAt - row.endOfSpeechAt;
  const serverMs = row.analysisAt === undefined ? undefined : row.analysisAt - row.submittedAt;
  const voiceMs =
    row.speechStartAt === undefined || row.resultAt === undefined ? undefined : row.speechStartAt - row.resultAt;
  // Until speech is wired (or when it fails), the caption release stands in for audio start.
  const totalMs =
    serverMs === undefined || !row.spoken ? undefined : recognitionMs + serverMs + (voiceMs ?? 0);
  return { recognitionMs, serverMs, voiceMs, totalMs };
}

export function median(values: (number | undefined)[]): number | undefined {
  const known = values.filter((v): v is number => v !== undefined);
  if (!known.length) return undefined;
  const sorted = [...known].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

export function toCsv(rows: LatencyRow[]): string {
  const header = "turnId,speaker,recognitionMs,serverMs,voiceMs,totalMs";
  const lines = rows.map((r) => {
    const s = segments(r);
    return [r.turnId, r.speaker, s.recognitionMs, s.serverMs ?? "", s.voiceMs ?? "", s.totalMs ?? ""].join(",");
  });
  return [header, ...lines].join("\n");
}
