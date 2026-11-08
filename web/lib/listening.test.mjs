// Unit tests for recognition locales and hands-free listening rules (continuous-listening). Usage: npm test
import assert from "node:assert/strict";
import { test } from "node:test";
import { LANGUAGE_LABELS, RECOGNITION, VOICES } from "./languages.ts";

test("Tamil is recognised as ta-IN, which Azure accepts, and keeps its Sri Lankan voice", () => {
  assert.equal(RECOGNITION["ta-LK"], "ta-IN");
  assert.equal(VOICES["ta-LK"], "ta-LK-SaranyaNeural");
});

test("every language has a recognition locale, and no recognition locale is ta-LK", () => {
  assert.deepEqual(Object.keys(RECOGNITION).sort(), Object.keys(LANGUAGE_LABELS).sort());
  assert.ok(!Object.values(RECOGNITION).includes("ta-LK"));
});

test("the other languages are recognised in their own locale", () => {
  for (const language of ["pa-IN", "fr-CA", "en-CA", "si-LK"]) assert.equal(RECOGNITION[language], language);
});
