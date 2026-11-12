// Unit tests for the record helpers (demo-night-mvp tasks 3.5 to 3.8; CDR-001, CDR-006, CDR-007). Usage: npm test
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  applyAmended,
  brokenEntryLabel,
  effective,
  isConfirmed,
  repeatedBy,
  resolveSources,
  summaryIndexOf,
  summaryReading,
  summarySpeechId,
  turnOfEntry,
  versions,
  visitChanged,
} from "./record.ts";

const caption = (turnId, speaker, sourceText, status = "final") => ({
  turnId,
  speaker,
  sourceLanguage: speaker === "patient" ? "pa-IN" : "en-CA",
  targetLanguage: speaker === "patient" ? "en-CA" : "pa-IN",
  sourceText,
  status,
  translation: status === "final" ? `[t] ${sourceText}` : null,
  toneLabel: status === "final" ? "respectful" : null,
  glossaryUsed: [],
  criticalValues: [],
  readbackConfirmed: false,
});

const t1 = caption("t1", "patient", "ਪੈਂਹਠ ਸਾਲ");
const lookup = (id) => (id === "t1" ? t1 : null);
const amend = (amendmentId, newText) => ({
  segmentId: "t1",
  by: "patient",
  action: "amend",
  newText,
  amendmentId,
  translation: `[t] ${newText}`,
  toneLabel: "respectful",
  criticalValues: [],
  entryId: amendmentId,
});

test("a correction keeps the original and becomes the current version (cdr_006)", () => {
  const after = applyAmended([], amend("a1", "ਪਚਵੰਜਾ ਸਾਲ"), lookup, "2026-11-19T19:00:00Z");
  assert.equal(after.length, 1);
  assert.equal(after[0].current, "a1");
  assert.equal(after[0].original.sourceText, "ਪੈਂਹਠ ਸਾਲ");
  assert.deepEqual(
    versions(t1, after[0]).map((v) => [v.version, v.sourceText, v.corrected]),
    [
      ["original", "ਪੈਂਹਠ ਸਾਲ", false],
      ["a1", "ਪਚਵੰਜਾ ਸਾਲ", true],
    ],
  );
  assert.equal(effective(t1, after[0]).sourceText, "ਪਚਵੰਜਾ ਸਾਲ");
});

test("the same correction twice is applied once", () => {
  const once = applyAmended([], amend("a1", "x"), lookup, "t");
  assert.equal(applyAmended(once, amend("a1", "x"), lookup, "t"), once);
});

test("a confirmation of an earlier version stops counting once a correction is applied (cdr_006)", () => {
  let h = applyAmended([], { segmentId: "t1", by: "patient", action: "confirm", version: "original", entryId: "c1" }, lookup, "t");
  assert.equal(isConfirmed(h[0]), true);
  h = applyAmended(h, amend("a1", "y"), lookup, "t");
  assert.equal(isConfirmed(h[0]), false);
  assert.equal(h[0].confirmed.version, "original");
});

test("an event for an unknown turn is ignored", () => {
  assert.deepEqual(applyAmended([], { ...amend("a1", "x"), segmentId: "nope" }, lookup, "t"), []);
});

test("the broken badge names a turn, a correction, or another entry (cdr_006, idr_003)", () => {
  const h = applyAmended([], amend("a1", "x"), lookup, "t");
  const ids = ["t0", "t1"];
  assert.equal(brokenEntryLabel(null, ids, h), null);
  assert.equal(brokenEntryLabel("t1", ids, h), "turn 2");
  assert.equal(brokenEntryLabel("a1", ids, h), "turn 2, correction");
  assert.equal(brokenEntryLabel("c9", ids, h, { consent: ["c9"] }), "consent");
  // CDR-008: a signal entry is named as the patient's, by its signalId.
  assert.equal(brokenEntryLabel("s1", ids, h, { signals: ["s1"] }), "a patient signal");
  assert.equal(brokenEntryLabel("zz", ids, h), "an earlier entry");
  assert.equal(turnOfEntry("a1", h), "t1");
  assert.equal(turnOfEntry("t0", h), "t0");
});

test("summary sentences are read in order as {summaryId}.{n} (cdr_007)", () => {
  const summary = {
    summaryId: "s7",
    sentences: [
      { sentenceId: "b", index: 1, text: "two", sources: [] },
      { sentenceId: "a", index: 0, text: "one", sources: [] },
    ],
  };
  assert.equal(summarySpeechId("s7", 2), "s7.2");
  assert.deepEqual(summaryReading(summary), [
    { speechId: "s7.0", text: "one" },
    { speechId: "s7.1", text: "two" },
  ]);
  assert.equal(summaryIndexOf("s7", "s7.1"), 1);
  assert.equal(summaryIndexOf("s7", "s70.1"), null);
  assert.equal(summaryIndexOf("s7", "turn-1"), null);
});

test("a note sentence's sources resolve to the turn at the cited version (cdr_007)", () => {
  const h = applyAmended([], amend("a1", "ਪਚਵੰਜਾ"), lookup, "t");
  const turns = [caption("t0", "physician", "Hello"), t1];
  const resolved = resolveSources(
    [
      { kind: "turn", id: "t1", version: "a1" },
      { kind: "turn", id: "t0", version: "original" },
      { kind: "interpreter_line", id: "l1", version: "original" },
      { kind: "turn", id: "missing", version: "original" },
    ],
    turns,
    h,
  );
  assert.deepEqual(
    resolved.map((r) => [r.turn.turnId, r.index, r.version.sourceText, r.version.corrected]),
    [
      ["t1", 1, "ਪਚਵੰਜਾ", true],
      ["t0", 0, "Hello", false],
    ],
  );
});

test("a blocked turn is repeated by the same speaker's next unblocked turn (tdm_002)", () => {
  const turns = [
    caption("p1", "physician", "0.4 mg", "blocked"),
    caption("x1", "patient", "ok"),
    caption("p2", "physician", "0.4 mg again", "blocked"),
    caption("p3", "physician", "0.4 mg"),
    caption("p4", "physician", "later", "blocked"),
  ];
  assert.deepEqual([...repeatedBy(turns)], [
    ["p1", "p3"],
    ["p2", "p3"],
  ]);
});

test("a visit.state for another visit is a new visit; the first one and repeats are not (cdr_001)", () => {
  const shown = { current: null };
  assert.equal(visitChanged(shown, "v1"), false); // first connect
  assert.equal(visitChanged(shown, "v1"), false); // a reconnect, or a state after visit.set_languages
  assert.equal(visitChanged(shown, "v2"), true); // visit.new
  assert.equal(shown.current, "v2");
  assert.equal(visitChanged(shown, "v2"), false);
});
