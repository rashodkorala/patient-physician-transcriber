// Unit tests for the trust helpers (trust-across-the-barrier review fixes; MDD-005, CDR-008). Usage: npm test
import assert from "node:assert/strict";
import { test } from "node:test";
import { SIGNAL_SHOWN_MS, insertTrust, lastSpokenIn, settledOrder, signalShownFor } from "./trust.ts";

const turnUpdate = (turnId) => ({
  turnId,
  speaker: "physician",
  emotion: null,
  manner: "plain",
  reassuranceLanded: null,
  signal: null,
  cue: null,
  at: "2026-11-11T10:00:00Z",
});
const signalUpdate = (turnId, signal) => ({ ...turnUpdate(turnId), speaker: null, manner: null, signal });
const listed = (list) => list.map((u) => `${u.turnId ?? "-"}${u.signal ? `:${u.signal}` : ""}`);

const turn = (turnId, status, targetLanguage = "pa-IN") => ({
  turnId,
  speaker: targetLanguage === "pa-IN" ? "physician" : "patient",
  sourceLanguage: targetLanguage === "pa-IN" ? "en-CA" : "pa-IN",
  targetLanguage,
  sourceText: `said ${turnId}`,
  translation: `relayed ${turnId}`,
  status,
});

test("cdr_008: a late turn update lands before the signal that followed its turn", () => {
  const order = ["t5"];
  let list = insertTrust([], signalUpdate("t5", "not_understood"), order);
  list = insertTrust(list, turnUpdate("t5"), order);
  assert.deepEqual(listed(list), ["t5", "t5:not_understood"]);
});

test("cdr_008: a late update for an earlier turn lands before a later turn's update and signals", () => {
  const order = ["t1", "t2"];
  let list = [];
  for (const u of [signalUpdate(null, "slower"), turnUpdate("t2"), signalUpdate("t2", "repeat"), turnUpdate("t1")]) {
    list = insertTrust(list, u, order);
  }
  assert.deepEqual(listed(list), ["-:slower", "t1", "t2", "t2:repeat"]);
  // Updates in order are simply appended, and two signals at one place keep their arrival order.
  list = insertTrust(list, signalUpdate("t2", "slower"), order);
  assert.deepEqual(listed(list), ["-:slower", "t1", "t2", "t2:repeat", "t2:slower"]);
});

test("cdr_008: the settled order after a reload follows the server's trust list, then the turn log", () => {
  // The dose (t1) was submitted first but confirmed after t2 was spoken, so the trust list has t2 before t1.
  const turns = [turn("t1", "readback_required"), turn("t2", "final", "en-CA"), turn("t3", "blocked"), turn("t4", "readback_required")];
  const trust = [turnUpdate("t2"), turnUpdate("t1"), signalUpdate("t1", "repeat")];
  assert.deepEqual(settledOrder(turns, trust, "t4"), ["t2", "t1", "t3"]);
});

test("cdr_008: the last translation spoken to the patient after a reload", () => {
  const turns = [turn("t1", "final"), turn("t2", "readback_required"), turn("t3", "final", "en-CA"), turn("t4", "readback_required")];
  // t2 was confirmed (it has its own trust update); t4 was rejected (it has none).
  const trust = [turnUpdate("t1"), turnUpdate("t2"), turnUpdate("t3")];
  const order = settledOrder(turns, trust, null);
  assert.deepEqual(lastSpokenIn(turns, trust, order, "pa-IN"), { text: "relayed t2", language: "pa-IN", speechId: "t2" });
  assert.equal(lastSpokenIn([turn("t3", "final", "en-CA")], [], ["t3"], "pa-IN"), null);
});

test("cdr_008: a live signal shows for the full time whatever the clocks say; a snapshot's for what is left", () => {
  const entry = { signalId: "s1", signal: "slower", afterTurnId: null, at: "2026-11-11T10:00:00Z" };
  const made = Date.parse(entry.at);
  // A screen whose clock runs 30 seconds ahead of the server's still shows a live signal.
  assert.equal(signalShownFor(entry, true, made + 30000), SIGNAL_SHOWN_MS);
  assert.equal(signalShownFor(entry, false, made + 3000), SIGNAL_SHOWN_MS - 3000);
  assert.ok(signalShownFor(entry, false, made + 30000) <= 0);
});
