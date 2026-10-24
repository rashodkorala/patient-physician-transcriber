/**
 * Per-turn latency log on the controller (task 1.7).
 * End of speech to translated audio starting is the figure that must stay under 3 seconds.
 */

export interface LatencyRow {
  turnId: string;
  speaker: string;
  endOfSpeechAt: number;
  resultAt?: number;
  speechStartAt?: number;
}

/** Until speech is wired (or when it fails), the result time stands in for audio start. */
export function totalMs(row: LatencyRow): number | undefined {
  const end = row.speechStartAt ?? row.resultAt;
  return end === undefined ? undefined : end - row.endOfSpeechAt;
}

export function median(values: number[]): number | undefined {
  if (!values.length) return undefined;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

export function toCsv(rows: LatencyRow[]): string {
  const header = "turnId,speaker,toResultMs,toSpeechMs,totalMs";
  const lines = rows.map((r) => {
    const toResult = r.resultAt ? r.resultAt - r.endOfSpeechAt : "";
    const toSpeech = r.speechStartAt && r.resultAt ? r.speechStartAt - r.resultAt : "";
    return [r.turnId, r.speaker, toResult, toSpeech, totalMs(r) ?? ""].join(",");
  });
  return [header, ...lines].join("\n");
}
