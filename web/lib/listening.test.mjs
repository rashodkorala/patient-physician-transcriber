// Unit tests for recognition locales and hands-free listening rules (continuous-listening). Usage: npm test
import assert from "node:assert/strict";
import { test } from "node:test";
import { LANGUAGE_LABELS, RECOGNITION, VOICES } from "./languages.ts";
import { isShortReply, listeningState, sideFor } from "./listening.ts";

const sides = (patientLanguage) => [
  { speaker: "physician", language: "en-CA", recognition: RECOGNITION["en-CA"] },
  { speaker: "patient", language: patientLanguage, recognition: RECOGNITION[patientLanguage] },
];

test("the detected locale decides the side, and Tamil heard as ta-IN is the patient in ta-LK", () => {
  assert.deepEqual(sideFor("en-CA", sides("pa-IN")), { speaker: "physician", language: "en-CA", recognition: "en-CA" });
  assert.deepEqual(sideFor("pa-IN", sides("pa-IN")), { speaker: "patient", language: "pa-IN", recognition: "pa-IN" });
  assert.deepEqual(sideFor("ta-IN", sides("ta-LK")), { speaker: "patient", language: "ta-LK", recognition: "ta-IN" });
});

test("English while a patient language is set routes to the physician side, translated for the patient", () => {
  assert.equal(sideFor("en-CA", sides("fr-CA")).speaker, "physician");
});

test("a locale outside the visit is no one's", () => {
  assert.equal(sideFor("fr-CA", sides("pa-IN")), null);
  assert.equal(sideFor("", sides("pa-IN")), null);
});

test("one- and two-word replies are short, whatever the script or punctuation", () => {
  for (const reply of ["Yes.", "We.", "Oui", "ਹਾਂ ਜੀ।", "ஆமாம்.", "ඔව්.", "Harpreet Kaur", "Ah, Mum.", "  ok  "]) {
    assert.equal(isShortReply(reply), true, reply);
  }
});

test("three words or more go straight through", () => {
  for (const turn of ["Yes, three days.", "ਮੈਨੂੰ ਸਿਰ ਦਰਦ ਹੈ।", "How have you been?", "எனக்கு மூன்று நாட்களாக தலைவலி"]) {
    assert.equal(isShortReply(turn), false, turn);
  }
});

test("push-to-talk outranks read-back, which outranks the voice, and only no reason means listening", () => {
  const none = { voice: false, readback: false, pushToTalk: false };
  assert.equal(listeningState(none), "listening");
  assert.equal(listeningState({ ...none, voice: true }), "voice");
  assert.equal(listeningState({ ...none, voice: true, readback: true }), "readback");
  assert.equal(listeningState({ voice: true, readback: true, pushToTalk: true }), "pushToTalk");
});

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
