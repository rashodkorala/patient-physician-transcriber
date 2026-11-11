// Unit tests for the notice files (trust-across-the-barrier task 1.2; CDR-008, IDR-005). Usage: npm test
// Reads the five language files directly, so a key added to one and forgotten in another fails here, before
// a screen falls back to an empty label in that language.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const LANGUAGES = ["en", "fr", "pa", "si", "ta"];
const read = (code) => JSON.parse(readFileSync(new URL(`../i18n/${code}.json`, import.meta.url), "utf8"));
const files = Object.fromEntries(LANGUAGES.map((code) => [code, read(code)]));
const keysOf = (file) => Object.keys(file).sort();

test("every language file has exactly the keys of en.json", () => {
  const english = keysOf(files.en);
  for (const code of LANGUAGES) {
    assert.deepEqual(keysOf(files[code]), english, `${code}.json has a different key set from en.json`);
  }
});

test("every notice is a non-empty string in every language", () => {
  for (const code of LANGUAGES) {
    for (const [key, value] of Object.entries(files[code])) {
      assert.equal(typeof value, "string", `${code}.json ${key} is not a string`);
      assert.ok(value.trim().length > 0, `${code}.json ${key} is empty`);
    }
  }
});

test("every file still waits for a native speaker's sign-off", () => {
  for (const code of LANGUAGES) assert.equal(files[code]._reviewer, "pending", `${code}.json`);
});

test("the patient's controls, the manner labels, and the stage lines exist (CDR-008, IDR-005)", () => {
  const needed = [
    "signalNotUnderstood",
    "signalSlower",
    "signalRepeat",
    "pause",
    "resume",
    "requestInterpreter",
    "signalNotUnderstoodNotice",
    "signalSlowerNotice",
    "signalRepeatNotice",
    "nothingToRepeat",
    "signalSent",
    "yourControls",
    "latestTitle",
    "speakerPhysician",
    "speakerPatient",
    "speakerCompanion",
    "stageListening",
    "stageTranslating",
    "mannerWarm",
    "mannerReassuring",
    "mannerGentle",
    "mannerSerious",
    "mannerUrgent",
    "mannerApologetic",
    "mannerEncouraging",
  ];
  for (const key of needed) assert.ok(key in files.en, `en.json lacks ${key}`);
});

test("no notice uses an em dash (project writing rule)", () => {
  for (const code of LANGUAGES) {
    for (const [key, value] of Object.entries(files[code])) {
      assert.ok(!value.includes("—"), `${code}.json ${key} contains an em dash`);
    }
  }
});
